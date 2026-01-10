project(
	'bottles',
	version: '60.1',
	meson_version: '>= 1.5.0',
	default_options: [
		'warning_level=2',
	],
	license: 'GPL-3.0-only'
)


APP_NAME = 'Bottles'
DEVELOPER_ID = 'com.usebottles'
BASE_ID = DEVELOPER_ID + '.' + meson.project_name()
APP_ID = BASE_ID
APP_VERSION = meson.project_version()
_version_array = APP_VERSION.split('.')
APP_MAJOR_VERSION = _version_array[0]
APP_MINOR_VERSION = _version_array[1]
PROFILE = get_option('profile')

BINARY_NAME = 'bottles'
CLI_BINARY_NAME = 'bottles-cli'

if PROFILE == 'development'
	git = find_program('git', required: false)
	if git.found()
		git_command = run_command(git, 'rev-parse', '--short', 'HEAD', check: false)
		if git_command.returncode() == 0
			APP_VERSION += '-' + git_command.stdout().strip()
		endif
	endif
	APP_NAME += ' (Development)'
	APP_ID += '.' + 'Devel'
	BINARY_NAME = 'bottles-devel'
	CLI_BINARY_NAME = 'bottles-devel-cli'
	GETTEXT_PACKAGE = BINARY_NAME
	pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), BINARY_NAME)
else
	GETTEXT_PACKAGE = meson.project_name()
	pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
endif

APP_ID_PATH = '/' + APP_ID.replace('.', '/') + '/'


gnome = import('gnome')
i18n = import('i18n')
localedir = get_option('localedir')

subdir('po')
subdir('bottles')
subdir('data')

gnome.post_install(
	glib_compile_schemas: true,
	gtk_update_icon_cache: true,
	update_desktop_database: true,
)
