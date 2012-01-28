import os


class PythonAppType(object):

    init_template = 'init-python'
    update_command = 'bin/pip install -r requirements.txt'

    def __init__(self, builder):
        self.init_template_context = {}

    @staticmethod
    def detected():
        return os.path.exists('requirements.txt')


class JavaScriptAppType(object):

    init_template = 'init-javascript'
    update_command = 'bin/node cotton-deploy/local/bin/npm install'

    def __init__(self, builder):
        self.init_template_context = {
            'app_name': builder.app_name
        }

    @staticmethod
    def detected():
        return os.path.exists('package.json')


# Detect the type of application within the given repo path.
def detect_app_type(builder):
    if PythonAppType.detected():
        return PythonAppType(builder)
    elif JavaScriptAppType.detected():
        return JavaScriptAppType(builder)
    return Exception('Unknown application type')
