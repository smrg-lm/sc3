
import setuptools


with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='sc3',
    version='0.0.1',
    author='Lucas Samaruga',
    author_email='samarugalucas@gmail.com',
    description='SuperCollider 3 class library Python 3 port',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/smrg-lm/sc3",
    packages=['sc3'],
    python_requires='>=3.6',
    install_requires=['pyliblo'],
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Development Status :: 1 - Planning',
    ],
    keywords='SuperCollider sound synthesis music composition'
)
