import vobject
import pandas as pd
from typing import List, Dict
import unicodedata

class VCFHandler:
    def __init__(self):
        self.supported_fields = ['FN', 'TEL', 'EMAIL', 'TYPE']
    
    def parse_vcf(self, filepath: str) -> pd.DataFrame:
        """
        VCF dosyasını okur ve DataFrame'e dönüştürür
        
        Args:
            filepath: VCF dosyasının yolu
            
        Returns:
            pd.DataFrame: VCF verilerini içeren DataFrame
        """
        contacts = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            vcards = vobject.readComponents(f)
            
            for vcard in vcards:
                contact = {
                    'Name': '',
                    'Phone': '',
                    'E-mail': '',
                    'Type': ''
                }
                
                # İsim
                if hasattr(vcard, 'fn'):
                    contact['Name'] = vcard.fn.value
                
                # Telefon
                if hasattr(vcard, 'tel'):
                    phones = []
                    types = []
                    for tel in vcard.tel_list:
                        phones.append(tel.value)
                        if hasattr(tel, 'type_param'):
                            types.append(tel.type_param)
                        else:
                            types.append('')
                    
                    contact['Phone'] = ';'.join(phones)
                    contact['Type'] = ';'.join(types)
                
                # E-posta
                if hasattr(vcard, 'email'):
                    emails = []
                    for email in vcard.email_list:
                        emails.append(email.value)
                    contact['E-mail'] = ';'.join(emails)
                
                contacts.append(contact)
        
        return pd.DataFrame(contacts)
    
    def _normalize_text(self, text: str) -> str:
        """
        Metni Unicode normalize eder ve Türkçe karakterleri düzeltir
        """
        if pd.isna(text):
            return text
        return unicodedata.normalize('NFC', str(text))
    
    def _split_name(self, name: str) -> tuple:
        """
        İsmi soyad, ad, orta ad olarak ayırır
        """
        if pd.isna(name):
            return ('', '', '', '')
        
        parts = name.split()
        if len(parts) == 1:
            return (parts[0], '', '', '')
        elif len(parts) == 2:
            return (parts[1], parts[0], '', '')
        else:
            # Son kelime soyad, ilk kelime ad, ortadaki kelimeler orta ad
            return (parts[-1], parts[0], ' '.join(parts[1:-1]), '')
    
    def export_vcf(self, df: pd.DataFrame, filepath: str, ios_compatible: bool = False) -> None:
        """
        DataFrame'i VCF dosyası olarak kaydeder
        
        Args:
            df: Kaydedilecek veriler
            filepath: Kaydedilecek dosya yolu
            ios_compatible: iOS uyumlu format kullanılsın mı?
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                if ios_compatible:
                    # iOS uyumlu format
                    f.write('BEGIN:VCARD\n')
                    
                    # İsim
                    if pd.notna(row['Name']):
                        name = self._normalize_text(row['Name'])
                        surname, firstname, middlename, prefix = self._split_name(name)
                        f.write(f'N:{surname};{firstname};{middlename};{prefix};\n')
                        f.write(f'FN:{name}\n')
                    
                    # Telefon
                    if pd.notna(row['Phone']):
                        phones = row['Phone'].split(';')
                        for phone in phones:
                            if phone.strip():
                                f.write(f'TEL;type=pref:{phone.strip()}\n')
                    
                    # E-posta
                    if pd.notna(row['E-mail']):
                        emails = row['E-mail'].split(';')
                        for email in emails:
                            if email.strip():
                                f.write(f'EMAIL:{email.strip()}\n')
                    
                    f.write('END:VCARD\n\n')
                else:
                    # Standart format
                    vcard = vobject.vCard()
                    
                    # İsim
                    if pd.notna(row['Name']):
                        vcard.add('fn')
                        vcard.fn.value = self._normalize_text(row['Name'])
                    
                    # Telefon
                    if pd.notna(row['Phone']):
                        phones = row['Phone'].split(';')
                        types = row['Type'].split(';') if pd.notna(row['Type']) else [''] * len(phones)
                        
                        for phone, type_ in zip(phones, types):
                            tel = vcard.add('tel')
                            tel.value = phone.strip()
                            if type_:
                                tel.type_param = type_
                    
                    # E-posta
                    if pd.notna(row['E-mail']):
                        emails = row['E-mail'].split(';')
                        for email in emails:
                            vcard.add('email')
                            vcard.email_list[-1].value = email.strip()
                    
                    f.write(vcard.serialize())
                    f.write('\n') 