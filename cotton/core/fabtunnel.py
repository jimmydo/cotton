# Based on this sample code:
# https://github.com/paramiko/paramiko/blob/master/demos/forward.py

import SocketServer
import contextlib
import fabric.api as fabapi
import fabric.network as fabnet
import select
import ssh
import threading

g_verbose = False


def verbose(s):
    if g_verbose:
        print s


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(SocketServer.BaseRequestHandler):

    def handle(self):
        request_peer_name = self.request.getpeername()
        try:
            chan = self.ssh_transport.open_channel(
                'direct-tcpip',
               (self.chain_host, self.chain_port),
               request_peer_name
            )
        except Exception, e:
            verbose('Incoming request to %s:%d failed: %s' % (
                self.chain_host,
                self.chain_port,
                repr(e)
            ))
            return
        if chan is None:
            verbose('Incoming request to %s:%d was rejected by the SSH server.' %
                    (self.chain_host, self.chain_port))
            return

        verbose('Connected! Tunnel open %r -> %r -> %r' % (
            request_peer_name,
            chan.getpeername(),
            (self.chain_host, self.chain_port)
        ))
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()
        verbose('Tunnel closed from %r' % (request_peer_name,))


def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHander (Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport
    server = ForwardServer(('', local_port), SubHander)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


class Tunneler(object):

    def __init__(self, bastion_username, bastion_host, bastion_key_path):
        self._bastion_username = bastion_username
        self._bastion_host = bastion_host
        self._bastion_port = 22
        self._bastion_key_path = bastion_key_path

    @contextlib.contextmanager
    def __call__(self):
        LOC_PORT = 9999

        username, host, port = fabnet.normalize(fabapi.env.host_string)
        port = int(port)

        # We can't seem to connect to the custom TCP server when we provide a
        # an address of 'localhost', but '127.0.0.1' works. A tunnel created
        # using the `ssh` command in the shell works for both addresses.
        # Issue is probably related to how the custom TCP server is created.
        host_string = '{0}@127.0.0.1:{1}'.format(username, LOC_PORT)

        client = ssh.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(ssh.WarningPolicy())
        client.connect(
            self._bastion_host,
            self._bastion_port,
            username=self._bastion_username,
            key_filename=self._bastion_key_path
        )
        server = forward_tunnel(
            LOC_PORT,
            host,
            port,
            client.get_transport()
        )

        with fabapi.settings(host_string=host_string):
            try:
                yield self
            finally:
                if server:
                    # Tell Fabric to close connection to tunnel.
                    fabnet.disconnect_all()

                    # Close tunnel through bastion server.
                    server.shutdown()

                    # Close connection to bastion server.
                    client.close()
