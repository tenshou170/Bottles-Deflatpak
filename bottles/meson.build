moduledir = join_paths(pkgdatadir, 'bottles')

python = import('python')

conf = configuration_data()
conf.set('PYTHON', '/usr/bin/python3')
conf.set('BASE_ID', BASE_ID)
conf.set('APP_ID', APP_ID)
conf.set('APP_NAME', APP_NAME)
conf.set('APP_VERSION', APP_VERSION)
conf.set('APP_MAJOR_VERSION', APP_MAJOR_VERSION)
conf.set('APP_MINOR_VERSION', APP_MINOR_VERSION)
conf.set('BINARY_NAME', BINARY_NAME)
conf.set('CLI_BINARY_NAME', CLI_BINARY_NAME)
conf.set('PROFILE', PROFILE)
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)
conf.set('GETTEXT_PACKAGE', GETTEXT_PACKAGE)

subdir('backend')
subdir('frontend')

bottles_sources = [
  '__init__.py',
]

install_data(bottles_sources, install_dir: moduledir)
