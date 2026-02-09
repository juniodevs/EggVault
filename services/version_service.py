import json
import os

class VersionService:
    CHANGELOG_FILE = 'changelog.json'

    @staticmethod
    def get_current_version():
        try:
            if os.path.exists(VersionService.CHANGELOG_FILE):
                with open(VersionService.CHANGELOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('currentVersion', '1.0.0')
            return '1.0.0'
        except Exception:
            return '1.0.0'

    @staticmethod
    def get_changelog():
        try:
            if os.path.exists(VersionService.CHANGELOG_FILE):
                with open(VersionService.CHANGELOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        'success': True,
                        'currentVersion': data.get('currentVersion', '1.0.0'),
                        'versions': data.get('versions', [])
                    }
            return {
                'success': False,
                'error': 'Changelog não encontrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
