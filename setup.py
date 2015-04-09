from distutils.core import setup

setup_args = dict(
    name="urwidgets",
    version="0.2",
    description="A collection of useful widgets to use with the urwid library",
    author="Chaise Conn",
    author_email="chaisecanz@gmail.com",
    url="https://github.com/Jdaco/urwidgets",
    platforms="Platform Independent",
    install_requires=['urwid'],
    packages=["urwidgets"],
)

setup(**setup_args)
