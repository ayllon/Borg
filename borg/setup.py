from distutils.core import setup


setup(
    name='borg',
    version='0.0.1',
    description='Test utility',
    author='Alejandro Alvarez Ayllon',
    license='Apache 2',
    packages=['borg'],
    install_requires=['locustio', 'nova-adminclient', 'sqlalchemy', 'paramiko'],
    entry_points = {
        'console_scripts': [
            'borg = borg.cli:main'
        ]
    }
)
