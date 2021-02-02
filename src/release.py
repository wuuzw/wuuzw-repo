# -*- coding: utf-8 -*-
import hashlib
import os
import zipfile
import sys
from distutils.version import StrictVersion
from lxml import etree


def build(plugin: str, version: str, message: str):
    plugin_dir = os.path.join(os.getcwd(), plugin)
    changelog_file = os.path.join(plugin_dir, 'changelog.txt')
    addon_file = os.path.join(plugin_dir, 'addon.xml')
    repo_addon_file = os.path.join(ROOT_DIR, 'addons.xml')

    # update version
    addon_tree = etree.parse(addon_file)
    addon = addon_tree.getroot()
    assert StrictVersion(version) > StrictVersion(
        addon.attrib['version']), f'new version must be greater than {addon.attrib["version"]}'
    addon.set('version', version)
    addon_tree.write(addon_file, encoding="UTF-8", pretty_print=True)

    # update changelog
    with open(changelog_file, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(f'{version}\n{message}\n\n{content}')
    f.close()

    # make zip file
    plugin_output = os.path.join(OUTPUT_DIR, plugin)
    if not os.path.exists(plugin_output):
        os.mkdir(plugin_output)

    archive = os.path.join(plugin_output, f'{plugin}-{version}.zip')
    f = zipfile.ZipFile(archive, 'w', zipfile.ZIP_STORED)
    for dir_path, dir_names, file_names in os.walk(plugin):
        for file_name in file_names:
            f.write(os.path.join(dir_path, file_name))
    f.close()

    # update repo addon.xml
    repo_tree = etree.parse(repo_addon_file)
    repo_addon = repo_tree.getroot()
    element = repo_addon.find(f"./addon[@id='{plugin}']")
    if element is not None:
        element.set('version', version)
    else:
        repo_addon.append(addon)
    repo_tree.write(repo_addon_file, encoding="UTF-8", pretty_print=True)

    # update md5
    md5 = generate_md5()
    with open(os.path.join(ROOT_DIR, 'addons.xml.md5'), 'w') as f:
        f.write(md5)
    f.close()


def generate_md5():
    return hashlib.md5(open(os.path.join(ROOT_DIR, 'addons.xml'), "rb", ).read()).hexdigest()


def main():
    if len(sys.argv) == 4:
        plugin = sys.argv[1]
        version = sys.argv[2]
        message = sys.argv[3]
        build(plugin, version, message)
    else:
        print(f'Usage: {sys.argv[0]} plugin_dir plugin_version message')


ROOT_DIR = os.path.abspath("..")
OUTPUT_DIR = os.path.join(ROOT_DIR, 'repo')

if __name__ == '__main__':
    main()
