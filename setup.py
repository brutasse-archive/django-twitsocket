# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-twitsocket',
    version='0.1',
    author=u'Bruno Renié, Gautier Hayoun',
    author_email='bruno@renie.fr',
    packages=find_packages(),
    include_package_data=True,
    url='http://github.com/brutasse/django-twitsocket',
    license='BSD',
    description='A twitter wall / live stream for your conference / event / topic of interest, as a Django reusable app.',
    long_description=read('README.rst'),
    zip_safe=False,
)

