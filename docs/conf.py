# -*- coding: utf-8 -*-

project = 'toasty'
author = 'Chris Beaumont and the AAS WorldWide Telescope Team'
copyright = '2014-2019, ' + author

release = '0.0.2'  # the full version string; also update ../setup.py
version = '0.0'  # the "short" version

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx_automodapi.automodapi',
    'sphinx_automodapi.smart_resolver',
    'numpydoc',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'
todo_include_todos = False

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
htmlhelp_basename = 'toastydoc'

intersphinx_mapping = {
    'python': (
        'https://docs.python.org/3/',
        (None, 'http://data.astropy.org/intersphinx/python3.inv')
    ),

    'numpy': (
        'https://docs.scipy.org/doc/numpy/',
        (None, 'http://data.astropy.org/intersphinx/numpy.inv')
    ),

    'astropy': (
        'http://docs.astropy.org/en/stable/',
        None
    ),
}

numpydoc_show_class_members = False

nitpicky = True
nitpick_ignore = [('py:class', 'ipywidgets.widgets.domwidget.DOMWidget')]

default_role = 'obj'

html_logo = 'images/logo.png'

linkcheck_retries = 5
linkcheck_timeout = 10
