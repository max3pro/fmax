import os
import zipfile
import pathlib
from core.commands import _fs_implements
from fman import DirectoryPaneCommand, show_alert, show_prompt, _get_app_ctxt, \
	load_json
from fman.url import as_url, splitscheme, join, basename, relpath, normalize, \
	as_human_readable, dirname
from fman.fs import touch, is_dir


class MaxUnZipSelected(DirectoryPaneCommand):
	def is_visible(self):
		return pathlib.Path(self.pane.get_file_under_cursor()).suffix in ['.zip', '.rar', '.7z', '.tar', '.gz']

	def __call__(self):
		selected_files = self.pane.get_selected_files()
		output = ""
		if len(selected_files) >= 1 or (len(selected_files) == 0 and self.get_chosen_files()):
			if len(selected_files) == 0 and self.get_chosen_files():
				selected_files.append(self.get_chosen_files()[0])
			dirPath = os.path.dirname(as_human_readable(selected_files[0]))
			unZipName = os.path.basename(as_human_readable(selected_files[0]))
			inFile = os.path.join(dirPath, unZipName)
			unZipDir = unZipName[:-4]
			unZipPath = os.path.join(dirPath, unZipDir)
			zipfile.ZipFile(inFile).extractall(path=unZipPath)
			self.pane.reload()
			output += "Files were unzipped to directory {0}".format(unZipDir)
		else:
			output += "No files or directories selected"
		show_alert(output)


def get_fs_scheme(pane):
	return splitscheme(pane.get_path())[0]


class MaxCreateFile(DirectoryPaneCommand):
	aliases = ('New file', 'Create file')

	def __call__(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		if file_under_cursor:
			default = basename(file_under_cursor)
		else:
			default = ''
		name, ok = show_prompt("New file", default)
		if ok and name:
			base_url = self.pane.get_path()
			# import ipdb; ipdb.set_trace()
			touch(join(base_url, name))
			self.set_cursor(base_url, name)

	def set_cursor(self, base_url, name):
		dir_url = join(base_url, name)
		effective_url = normalize(dir_url)
		select = relpath(effective_url, base_url).split('/')[0]
		if select != '..':
			try:
				self.pane.place_cursor_at(join(base_url, select))
			except ValueError as dir_disappeared:
				pass

	def is_visible(self):
		return True
	
class MaxGoUp(DirectoryPaneCommand):
	def __call__(self):
		pane = self.pane
		path_before = pane.get_path()
		def callback():
			path_now = pane.get_path()
			if path_now != path_before:
				cursor_dest = splitscheme(path_now)[0] + \
							  splitscheme(path_before)[1]
				try:
					pane.place_cursor_at(cursor_dest)
				except ValueError as dest_doesnt_exist:
					pane.move_cursor_home()
		parent_dir = dirname(path_before)
		try:
			pane.set_path(parent_dir, callback)
		except FileNotFoundError:
			pass

class MaxOpenIfDirectory(DirectoryPaneCommand):
	def __call__(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		if file_under_cursor:
			try:
				f_is_dir = is_dir(file_under_cursor)
			except OSError as e:
				show_alert(
					'Could not read from %s (%s)' %
					(as_human_readable(file_under_cursor), e)
				)
				return
			if f_is_dir:
				self.pane.set_path(file_under_cursor)
			else:
				# Archive handling:
				scheme, path = splitscheme(file_under_cursor)
				if scheme == 'file://':
					new_scheme = self._get_handler_for_archive(path)
					if new_scheme:
						new_url = new_scheme + path
						self.pane.run_command(
							'open_directory', {'url': new_url}
						)
	def _get_handler_for_archive(self, file_path):
		settings = load_json('Core Settings.json', default={})
		archive_types = sorted(
			settings.get('archive_handlers', {}).items(),
			key=lambda tpl: -len(tpl[0])
		)
		for suffix, scheme in archive_types:
			if file_path.lower().endswith(suffix):
				return scheme
	def is_visible(self):
		return False