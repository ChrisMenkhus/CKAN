GITHUB_API = 'https://api.github.com'
CKAN_CORE_VERSION_STRING = 'private readonly static string BUILD_VERSION = null;'
CKAN_CORE_VERSION_STRING_TARGET = 'private readonly static string BUILD_VERSION = "%s";'

# ---* DO NOT EDIT BELOW THIS LINE *---

import os, sys

import urllib
import requests
from urlparse import urljoin

import datetime
import base64

import json
import shutil

def run_git_clone(repo, commit_hash):
    if os.path.isdir(repo):
        shutil.rmtree(repo)
    
    cwd = os.getcwd()
    if os.system('git clone https://github.com/KSP-CKAN/%s.git' % repo) != 0:
        sys.exit(1)
        
    os.chdir(os.path.join(cwd, repo))
    
    if commit_hash != 'master':
        if os.system('git checkout -f %s' % commit_hash) != 0:
            sys.exit(1)
        
    os.chdir(cwd)

def build_repo(repo):
    cwd = os.getcwd()
    os.chdir(os.path.join(cwd, repo))

    if os.system('sh build.sh') != 0:
        sys.exit(1)

    os.chdir(cwd)
    
def stamp_ckan_version(version):
    cwd = os.getcwd()
    os.chdir(os.path.join(cwd, 'CKAN-core'))
    
    meta_contents = None
    
    with open('Meta.cs', 'r') as meta_file:
        meta_contents = meta_file.read()
    
    if meta_contents == None:
        print 'Error reading Meta.cs'
        sys.exit(1)
    
    meta_contents = meta_contents.replace(CKAN_CORE_VERSION_STRING, CKAN_CORE_VERSION_STRING_TARGET % version)
    
    with open("Meta.cs", "w") as meta_file:
        meta_file.write(meta_contents)
        
    os.chdir(cwd)
    
def build_ckan(core_hash, gui_hash, cmdline_hash, release_version):
    if core_hash == None:
        core_hash = 'master'
    if gui_hash == None:
        gui_hash = 'master'
    if cmdline_hash == None:
        cmdline_hash = 'master'
    
    print 'Building CKAN from the following commit hashes:'
    print 'CKAN-core: %s' % core_hash
    print 'CKAN-GUI: %s' % gui_hash
    print 'CKAN-cmdline: %s' % cmdline_hash
    
    run_git_clone('CKAN-core', core_hash)
    run_git_clone('CKAN-GUI', gui_hash)
    run_git_clone('CKAN-cmdline', cmdline_hash)
    
    if release_version != None:
        stamp_ckan_version(release_version)
    
    build_repo('CKAN-core')
    build_repo('CKAN-GUI')
    build_repo('CKAN-cmdline')
    
    print 'Done!'

def make_github_post_request(url_part, username, password, payload):
    url = urljoin(GITHUB_API, url_part)
    print '::make_github_post_request - %s' % url
    return requests.post(url, auth = (username, password), data = json.dumps(payload), verify=False)

def make_github_get_request(url_path, username, password, payload):
    url = urljoin(GITHUB_API, url_path)
    print '::make_github_get_request - %s' % url
    return requests.get(url, auth = (username, password), data = json.dumps(payload), verify=False)

def make_github_put_request(url_path, username, password, payload):
    url = urljoin(GITHUB_API, url_path)
    print '::make_github_put_request - %s' % url
    return requests.put(url, auth = (username, password), data = json.dumps(payload), verify=False)

def make_github_post_request_raw(url_part, username, password, payload, content_type):
    url = urljoin(GITHUB_API, url_part)
    print '::make_github_post_request_raw - %s' % url

    headers = { 'Content-Type': content_type }
    return requests.post(url, auth = (username, password), data = payload, verify=False, headers=headers)

def make_github_release(username, password, repo, tag_name, name, body, draft, prerelease):
    payload = {}
    payload['tag_name'] = tag_name
    payload['name'] = name
    payload['body'] = body
    payload['draft'] = draft
    payload['prerelease'] = prerelease
    return make_github_post_request('/repos/%s/releases' % repo, username, password, payload)

def make_github_release_artifact(username, password, upload_url, filepath, content_type = 'application/zip'):
    filename = os.path.basename(filepath)
    query = { 'name': filename }
    url = '%s?%s' % (upload_url[:-7], urllib.urlencode(query))
    payload = file(filepath, 'r').read()
    return make_github_post_request_raw(url, username, password, payload, content_type)

def get_github_file(username, password, repo, path):
    return make_github_get_request('/repos/%s/contents/%s' % (repo, path), username, password, {})

def push_github_file_sha(username, password, repo, path, sha, content, branch='master'):
    payload = {}
    payload['path'] = path
    payload['message'] = 'Updating build-tag'
    payload['content'] = base64.b64encode(content)
    payload['sha'] = sha
    payload['branch'] = branch
    return make_github_put_request('/repos/%s/contents/%s' % (repo, path), username, password, payload)

def push_github_file(username, password, repo, path, content, branch='master'):
    response = get_github_file(username, password, repo, path)
    if response.status_code >= 400:
        print 'There was an issue fetching "%s"! Status: %s - %s' % (path, str(response.status_code), response.text)
        sys.exit(1)
        
    response_json = json.loads(response.text)
    return push_github_file_sha(username, password, repo, response_json['path'], response_json['sha'], content)
