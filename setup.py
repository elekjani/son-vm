from setuptools import setup, find_packages

setup(
        name='sonata-vm-manager',
        version='1.0',
        url='https://github.com/elekjani/son-vm',
        author_email='janos.elek@intec.ugent.be',
        package_dir={'': 'src'},
        packages=find_packages('src'),  # dependency resolution
        namespace_packages=['son', ],
        install_requires=['setuptools', 'twisted'],
        zip_safe=False,
        entry_points={
            'console_scripts': [
                'son-vm-server=son.vmmanager:main'
            ],
        },
        test_suite='test'
    )
