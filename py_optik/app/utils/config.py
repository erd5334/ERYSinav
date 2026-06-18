import configparser
import os

class ConfigManager:
    def __init__(self, filename='Ayarlar.ini'):
        self.filename = filename
        self.config = configparser.ConfigParser()
        if os.path.exists(self.filename):
            self.config.read(self.filename, encoding='utf-8')
        else:
            # Varsayılan değerlerle oluştur
            self.config['Sorular'] = {'Soru sayısı': '20'}
            self.config['Panel Ayarları'] = {
                'Panel Dikey Kenar Yüksekliği': '0',
                'Panel Yatay Kenar Uzunluğu': '0'
            }
            self.config['DKenarlar'] = {
                'Sol': '0', 'Sag': '0', 'Ust': '0', 'Alt': '0'
            }
            self.save()

    def get(self, section, key, default=''):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def get_int(self, section, key, default=0):
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def set(self, section, key, value):
        if section not in self.config:
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        self.save()

    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
