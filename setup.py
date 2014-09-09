from setuptools import setup

setup(name='warg', version='1.0.0',
      description='OpenShift Python-2.7 Community Cartridge based application',
      author='Ievgenii Petrenko', author_email='ievgeniip@gmail.com',
      url='http://www.python.org/sigs/distutils-sig/',

      #  Uncomment one or more lines below in the install_requires section
      #  for the specific client drivers/modules your application needs.
      install_requires=['greenlet', 'gevent<=1.0.0', 'Flask>=0.7.2', 'MarkupSafe',
                      'http',
                      'redis',
                      'pillow',
                      'Whoosh',
                      'apscheduler',
                      'gevent-websocket',
                      'simplejson',
                      'Flask-OAuth',
                      'requests',
                        #  'MySQL-python',
                        #  'pymongo',
                        #  'psycopg2', 
      ],
     )
