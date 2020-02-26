#!/usr/bin/env python3

from setuptools import setup

reflex_version="0.9.2"

reflex_classifiers=[
    'Environment :: Console :: Curses',
    'Environment :: Console',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Natural Language :: English',
    'Operating System :: Unix',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python',
    'Topic :: Multimedia :: Video :: Display'
]

with open("README.md", "r") as fp:
    reflex_long_description = fp.read()

setup(
    name="reflex-curses",
    author="Foldex",
    author_email="foldex@pm.me",
    classifiers=reflex_classifiers,
    description="TUI/CLI wrapper around streamlink for twitch.tv",
    entry_points={
        'console_scripts': [
            'reflex-curses = reflex_curses.reflex:main',
        ],},
    install_requires=["requests"],
    keywords="tui cli twitch streamlink",
    license="GPLv3",
    long_description=reflex_long_description,
    long_description_content_type='text/markdown',
    packages=["reflex_curses"],
    python_requires=">=3.6",
    url="https://github.com/foldex/reflex-curses",
    version=reflex_version,
    zip_safe=True
)
