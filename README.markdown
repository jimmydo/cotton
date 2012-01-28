Cotton
======

A framework for Heroku-like deployments.

I'm currently using it for a deployment in Amazon EC2, but the goal is for it to work in any hosting environment.

Pre-setup
---------

1. Create an empty `build repo`. You'll need its URL. Example: git@github.com:jimmydo/myproject-builds.git
2. Make sure you have a server to deploy to. You'll needs its IP address. Example: 10.0.1.240
3. Make sure the server has the appropriate SSH keys so that it can clone the `build repo` URL.

Project repo setup
------------------

On your development machine:

1. Run: sudo pip install fabric
2. Copy the `cotton` directory (right next to this README file) to the root of your project's git repo
3. Add this to your .gitignore: *.pyc
4. Create cotton-config.yml at the root of your project repo:

        my-app: # Name for deployment. Other examples: deployment, staging, testing
            build_repo: git@github.com:jimmydo/myproject-builds.git
            ports:
                web: 5000 # The port that the web process should listen on.
            remote_user: ubuntu # user account on server
            remote_home: /home/ubuntu # home directory on server
            key_path: /path/to/ec2/ssh-key.pem # private key for accessing server
            servers:
                10.0.1.240: [web] # server IP and the process types that should run on the server
            run_server: 10.0.1.240 # server on which one-off commands should be run

5. Add the new files and commit
6. Run: cotton/init

Now your project is setup to use Cotton.

After a fresh clone of your project repo, remember to run this once from the root of the project repo:

    cotton/init

This will create some supporting directories and files on your machine.

Commands
--------

- Build the latest commit of the 'master' branch of your local repo:

        git push -f cotton master

- Build the latest commit of the 'mybranch' branch of your local repo:

        git push -f cotton mybranch:master

- Deploy the latest build:

        cotton/deploy --app my-app

- Run a one-off command remotely:

        cotton/run --app my-app echo Hello World

- View config vars

        cotton/config --app my-app

- Add config vars

        cotton/config-add --app appname KEY1=value1 KEY2=value2

- Remove config vars

        cotton/config-remove --app appname KEY1 KEY2
