import argparse


class CottonArgParser(argparse.ArgumentParser):

    def __init__(self, proj_config, *args, **kwargs):
        super(CottonArgParser, self).__init__(*args, **kwargs)
        self.add_argument('--app', dest='app_name', choices=proj_config.keys(), required=True)
