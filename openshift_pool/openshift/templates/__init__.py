import glob
import os

from jinja2 import Template

from openshift_pool.common import AttributeDict


templates = AttributeDict()
for template_path in glob.glob('{}/*.j2'.format(os.path.dirname(__file__))):
    with open(template_path, 'r') as template:
        templates[os.path.basename(template_path).split('.')[0]] = Template(template.read())
