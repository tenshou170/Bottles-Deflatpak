clidir = join_paths(pkgdatadir, 'bottles/frontend/cli')

bottles_sources = [
  '__init__.py',
]

install_data(bottles_sources, install_dir: clidir)

configure_file(
  input: 'cli.py',
  output: CLI_BINARY_NAME,
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: ['rwxr-xr-x']
)
