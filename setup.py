
import setuptools


with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='sc3', # NOTE: no entiendo por qué el nombre de usuario para no pisar otro paquete, queda en el nombre?
    version='0.0.1', # NOTE: https://www.python.org/dev/peps/pep-0440/ for tuning.
    author='Lucas Samaruga',
    author_email='samarugalucas@gmail.com',
    description='SuperCollider 3 class library Python 3 port',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/smrg-lm/sc3",
    #packages=setuptools.find_packages(exclude=['devtools', 'docs', 'looseparts', 'tests']), # NOTE: o poner ['sc3'], pero no se si luego voy a hacer subpaquetes. No es recomendable hacer subpaquetes por el anidamiento según dice el estilo.
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
