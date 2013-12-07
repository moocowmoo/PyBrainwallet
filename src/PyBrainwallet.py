#!/usr/bin/python
import wx
import qrcode
from Crypto.Cipher import AES
from pybitcointools import *
from diceware import *
import scrypt
import hashlib
import binascii
import base58
import os
try:
    from PIL import Image
except ImportError:
    import Image
from PIL import ImageFont
from PIL import ImageDraw
import messages

# sudo apt-get update
# sudo apt-get install python-pip python-dev build-essential
# sudo apt-get install python-wxgtk2.8 python-wxtools wx2.8-i18n libwxgtk2.8-dev
# sudo pip install qrcode six pycrypto pillow scrypt base58
# wget github.com/vbuterin/pybitcointools/archive/master.zip
# extract, cd to directory
# sudo python setup.py install

# scrypt will build on Windows 7, using PyPi source, with MinGW

#############################################################################
## This work is free. You can redistribute it and/or modify it under the    #
## terms of the Do What The Fuck You Want To Public License, Version 2,     #
## as published by Sam Hocevar. See http://www.wtfpl.net/ for more details. #
#############################################################################

## TODO:
# Sizers - style issues with absolute layout
# Migrate more strings to messages.py
# Add Diceware button to UI
# Investigate scrypt module issue with PyInstaller/Windows
# Expand tests
# Investigate alternate hash algos, halting KDF

version = '0.43'

class Brainwallet(wx.Frame):

    def __init__(self,parent,id):
        wx.Frame.__init__(self,parent,id,
                          'PyBrainwallet',
                          size=(620,620))

        panel=wx.Panel(self)

        # Buttons and checkboxes
        self.compressCB = wx.CheckBox(panel, -1, "Compress",
                                      (6, 522), (-1, -1))
        self.bip32seedCB = wx.CheckBox(panel, -1, "BIP32 secret",
                                   (106, 522), (-1, -1))
        self.bip38CB = wx.CheckBox(panel, -1, "BIP38",
                                   (212, 522), (-1, -1))
        self.multihashCB = wx.CheckBox(panel, -1, "Multihash",
                                       (282, 522), (-1, -1))
        
        gen_button=wx.Button(panel,
                                 label='Text',
                                 pos=(5,490),
                                 size=(85,30))
        
        gen_file_button=wx.Button(panel,
                                 label='File(s)',
                                 pos=(95,490),
                                 size=(85,30))

        save_button=wx.Button(panel,
                              label='Save Note',
                              pos=(185,490),
                              size=(85,30))
        
        decrypt_button=wx.Button(panel,
                                 label='Decrypt',
                                 pos=(275,490),
                                 size=(85,30))
        
        test_button=wx.Button(panel,
                              label='Run Tests',
                              pos=(365,490),
                              size=(85,30))
        
        close_button=wx.Button(panel,
                               label='Exit',
                               pos=(455,490),
                               size=(85,30))

        # Bindings
        self.Bind(wx.EVT_TEXT_ENTER, self.seed_changed)
        self.Bind(wx.EVT_CHECKBOX, self.set_multihash, self.multihashCB)
        self.Bind(wx.EVT_CHECKBOX, self.set_bip32seed, self.bip32seedCB)
        self.Bind(wx.EVT_CHECKBOX, self.set_bip38, self.bip38CB)
        self.Bind(wx.EVT_CHECKBOX, self.set_compress, self.compressCB)
        self.Bind(wx.EVT_BUTTON,self.generate,gen_button)
        self.Bind(wx.EVT_BUTTON,self.generate_from_file,gen_file_button)
        self.Bind(wx.EVT_BUTTON,self.save_note,save_button)
        self.Bind(wx.EVT_BUTTON,self.decrypt_priv,decrypt_button)
        self.Bind(wx.EVT_BUTTON,self.close,close_button)
        self.Bind(wx.EVT_BUTTON,self.run_tests,test_button)
        self.Bind(wx.EVT_CLOSE,self.close)

        # Menu and Statusbar
        status=self.CreateStatusBar()
        menubar=wx.MenuBar() # Unity "global_menu" displays in Desktop topbar
        file_menu=wx.Menu()
        options_menu=wx.Menu()
        about_menu=wx.Menu()
        
        menubar.Append(file_menu,'File')
        menu_save_note=file_menu.Append(wx.NewId(),'Save Note',
                                        'Save current note to disk')
        self.Bind(wx.EVT_MENU,self.save_note,menu_save_note)

        menu_copy_addr=file_menu.Append(wx.NewId(),'Copy Address',
                                        'Copy address to clipboard')
        self.Bind(wx.EVT_MENU,self.copy_addr,menu_copy_addr)

        menu_copy_priv=file_menu.Append(wx.NewId(),'Copy Private Key',
                                        'Copy private key to clipboard')
        self.Bind(wx.EVT_MENU,self.copy_private,menu_copy_priv)
        
        menubar.Append(options_menu,'Options')
        menu_refresh=options_menu.Append(wx.NewId(),'Diceware PRNG',
                                         'Generate Diceware phrase with PRNG')
        self.Bind(wx.EVT_MENU,self.PRNG_passphrase,menu_refresh)
        
        menu_refresh=options_menu.Append(wx.NewId(),'Diceware Manual Rolls',
                                         'Generate Diceware phrase from physical dice rolls')
        self.Bind(wx.EVT_MENU,self.dice_passphrase,menu_refresh)
        
        menu_refresh=options_menu.Append(wx.NewId(),'Refresh',
                                         'Force refresh')
        self.Bind(wx.EVT_MENU,self.refresh,menu_refresh)
        
        menubar.Append(about_menu,'About')
        menu_about_about=about_menu.Append(wx.NewId(),'About',
                                           'PyBrainwallet version %s' % (version))
        self.Bind(wx.EVT_MENU,self.on_about,menu_about_about)
        
        menu_about_license=about_menu.Append(wx.NewId(),'License',
                                             ('WTFPL, Version 2'))
        self.Bind(wx.EVT_MENU,self.on_license,menu_about_license)
        
        menu_about_security=about_menu.Append(wx.NewId(),'Security',
                                              'Basic security guidelines')
        self.Bind(wx.EVT_MENU,self.on_security,menu_about_security)
        
        self.SetMenuBar(menubar)
        
        # flags
        self.multinotice = False
        self.multihash = False
        self.filelast = False
        self.compressed = False
        self.bip38 = False
        self.bip32 = False
        self.tests_passed = 'Untested'
        
        # initial keypair
        self.displayaddr = '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T'
        self.displaypriv = '5KJvsngHeMpm884wtkJNzQGaCErckhHJBGFsvd3VyK5qMZXj3hS'
        self.keypair_from_textseed('correct horse battery staple')

        # text/display
        self.test_static=wx.StaticText(panel,-1,'Tests:',(5,9),(200,-1),wx.ALIGN_LEFT)
        self.test_text=wx.TextCtrl(self, value=self.tests_passed,pos=(44,5), size=(550,-1),
                                   style=wx.TE_RICH|wx.TE_LEFT|wx.TE_READONLY)

        self.seed_static=wx.StaticText(panel,-1,'Seed:',(5,42),(200,-1),wx.ALIGN_LEFT)
        self.seed_text=wx.TextCtrl(self, value=self.seed, pos=(44,37), size=(550,-1),
                                   style=wx.TE_PROCESS_ENTER)
        
        self.address_static=wx.StaticText(panel,-1,'Address:',(5,68),(200,-1),wx.ALIGN_LEFT)
        self.address_text=wx.TextCtrl(self, value=self.displayaddr,pos=(4,88), size=(590,-1),
                                      style=wx.TE_READONLY|wx.TE_LEFT)
        
        self.privkey_static=wx.StaticText(panel,-1,'Private Key (WIF):',(4,118),(200,-1),
                                          wx.ALIGN_LEFT)
        self.privkey_text=wx.TextCtrl(self, value=self.displaypriv,pos=(5,138), size=(590,-1),
                                      style=wx.TE_READONLY|wx.TE_LEFT)
        
        # Note display
        self.notedisplay = wx.StaticBitmap(panel, pos=(10,170),size=(580,310))

        # make sure everything is loaded
        self.update_output()

        # init diceware
        self.dice = diceware()
        
        # TODO expand test cases, compressed, BIP38, multihash, decrypt
        # TODO move tests to tests.py
        self.tests = [{'seed':'I\'m a little teapot',
                       'privkey':'5KDWo5Uk6XNXF91dFPQUHbMvB7DxopoXVgusthKs2x13XJ3N3si',
                       'address':'19wUqefQsQmovScfjRtYBotAcvyHEKK4gs'},
                      {'seed':'Testing One Two Three',
                       'privkey':'5K6X2vmUtZ5xzAzAQ6vGz5PhEHLVNNpcaPFjAnXLxTBHt4NN8hb',
                       'address':'15gJ8SHCaQMvBqfmh2x9mwnozwWGDp2Xzd'},
                      {'seed':'NSA spying is illegal',
                       'privkey':'5JNoqh5rGvMuZuadesVE9iTNs3fkXFpNsTJgPZ1RR1FQMVwT37B',
                       'address':'1A2g7uRxGj4WRscoYSfY48A96QMyRJukJJ'},
                      {'seed':'correct horse battery staple',
                       'privkey':'5KJvsngHeMpm884wtkJNzQGaCErckhHJBGFsvd3VyK5qMZXj3hS',
                       'address':'1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T'}]

    def update_output(self, event=None):
        '''Update all displayed values on main panel.'''
        self.test_text.SetValue(self.tests_passed)
        if type(self.seed) == 'list':
            seedtext = ''
            for filename in self.seed:
                seedtext += filename+' '
            self.seed_text.SetValue(seedtext)
        else:
            self.seed_text.SetValue(self.seed)
        if self.bip38:
            self.encrypt_priv() # force update bip38 privkey
        if self.compressed:
            self.address_static.SetLabel('Compressed Address:')
            self.displayaddr = self.caddress
            if self.bip38:
                self.privkey_static.SetLabel('Privkey (BIP38):')
                self.displaypriv = self.bip38priv
            if not self.bip38:
                self.privkey_static.SetLabel('Compressed Privkey (WIF):')
                self.displaypriv = self.cprivkeywif
        if not self.compressed:
            self.address_static.SetLabel('Address:')
            self.displayaddr = self.address
            if not self.bip38:
                self.privkey_static.SetLabel('Privkey (WIF):')
                self.displaypriv = self.privkeywif
            if self.bip38:
                self.privkey_static.SetLabel('Privkey (BIP38):')
                self.displaypriv = self.bip38priv
        self.address_text.SetValue(self.displayaddr)
        self.privkey_text.SetValue(self.displaypriv)
        self.build_note(self.displayaddr,self.displaypriv)
        self.notedisplay.SetBitmap(self.displaynote)
        if self.tests_passed == 'Passed':
            self.test_text.SetForegroundColour((0,180,42))
        elif self.tests_passed == 'Failed':
            self.test_text.SetForegroundColour(wx.BLACK)
            self.test_text.SetBackgroundColour(wx.RED)

    def PRNG_passphrase(self,event):
        numwords = self.prng_dialog()
        if type(numwords) == int:
            self.seed = self.dice.prng(numwords)
            self.keypair_from_textseed(self.seed)
            self.update_output()

    def dice_passphrase(self,event):
        rolls = self.dice_dialog()
        if len(rolls) > 0:
            self.seed = self.dice.roll(rolls)
            self.keypair_from_textseed(self.seed)
            self.update_output()

    def seed_changed(self,event):
        '''Update output if user changes seed and presses Enter key'''
        self.keypair_from_textseed(self.seed_text.GetValue())
        self.update_output()

    def set_multihash(self, event):
        if self.seed == 'N/A':
            self.multihashCB.SetValue(False)
            return
        self.multihash = event.IsChecked()
        if not self.multinotice:
            self.multihash_notice()
        if event.IsChecked():
            self.multihash_dialog()
        if self.filelast:
            self.determine_keys(self.fileseed)
        else:
            self.determine_keys(self.seed)
        self.update_output()

    def set_bip38(self,event):
        self.bip38 = event.IsChecked()
        if event.IsChecked():
            self.bip38_dialog()
        if self.bip38:
            self.encrypt_priv()
        self.update_output()

    def set_bip32seed(self,event):
        self.bip32 = event.IsChecked()
        self.seed_changed(event)
        self.update_output()

    def set_compress(self,event):
        self.compressed = event.IsChecked()
        if self.bip38: # re-encrypt, using compressed wif
            self.encrypt_priv()
        self.update_output()

    def on_about(self,event):
        '''Dialog triggered by About option in About menu.'''
        aboutnotice = wx.MessageDialog(None,
                                       messages.about,
                                       'About PyBrainwallet',
                                       wx.OK | wx.ICON_INFORMATION)
        aboutnotice.ShowModal()
        aboutnotice.Destroy()
        
    def on_security(self, event):
        '''Dialog triggered by Security option in About menu.'''
        secnotice = wx.MessageDialog(None,
                                messages.security,
                                'Security', wx.OK | wx.ICON_INFORMATION)
        secnotice.ShowModal()
        secnotice.Destroy()

    def on_license(self,event):
        '''Dialog triggered by License option in About menu.'''
        licensenotice = wx.MessageDialog(None,
                                         messages.softwarelicense,
                                         'PyBrainwallet License',
                                         wx.OK | wx.ICON_INFORMATION)
        licensenotice.ShowModal()
        licensenotice.Destroy()

    def copy_addr(self,event):
        '''Copies displayed address to clipboard.'''
        clipboard = wx.TextDataObject()
        clipboard.SetText(self.address)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(clipboard)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Can't access the clipboard.", "Error")

    def copy_private(self,event):
        '''Copies displayed privkey to clipboard.'''
        clipboard = wx.TextDataObject()
        clipboard.SetText(self.privkeywif)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(clipboard)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Can't access the clipboard.", "Error")

    def address_from_privkey(self, privkey):
        '''Returns address derived from privkey, as string.'''
        return privtopub(privkey)

    def privkey_from_seed(self, seed):
        '''Returns privkey as int, via sha256 hash of given seed.'''
        return sha256(seed)
        
    def keypair_from_textseed(self, seed):
        '''Generate a keypair from text seed. Returns dict.'''
        self.filelast = False
        self.seed = seed
        self.determine_keys(seed)
        return {'privkeywif':self.privkeywif,
                'address':self.address}

    def keypair_from_fileseed(self, filelist, filepaths):
        '''Generate a keypair from list of file(s). Returns dict.'''
        self.filelast = True
        # for display, store filename(s) in self.seed
        self.seed = ''
        for filename in filelist:
            self.seed += filename+', '
        self.seed = self.seed[:-2]
        # operate on self.fileseed
        self.fileseed = ''
        if len(filepaths) == 1:
            self.fileseed = file(filepaths[0],'rb+').read()
        else:
            for filepath in filepaths:
                self.fileseed += file(filepath,'rb+').read()
                len(self.fileseed)
        self.determine_keys(self.fileseed)
        return {'privkeywif':self.privkeywif,
                'address':self.address}

    def to_bytes_32(self,v):
        """
        The MIT License (MIT)
        Copyright (c) 2013 by Richard Kiss
        """
        v = self.from_long(v, 0, 256, lambda x: x)
        if len(v) > 32:
            raise ValueError("input to to_bytes_32 is too large")
            return ((b'\0' * 32) + v)[-32:]
        return v

    def from_long(self, v, prefix, base, charset):
        """
        The MIT License (MIT)
        Copyright (c) 2013 by Richard Kiss
        """
        """The inverse of to_long. Convert an integer to an arbitrary base.

        v: the integer value to convert
        prefix: the number of prefixed 0s to include
        base: the new base
        charset: an array indicating what printable character to use for each value.
        """
        l = bytearray()
        while v > 0:
            try:
                v, mod = divmod(v, base)
                l.append(charset(mod))
            except Exception:
                raise ValueError("can't convert to character corresponding to ")
        l.extend([charset(0)] * prefix)
        l.reverse()
        return bytes(l)

    def determine_keys(self, seed):
        if not self.seed == 'N/A':
            if self.multihash:
                for i in range(1,self.multihash_numrounds):
                    seed = sha256(seed)
            if self.bip32:
                self.privkey = binascii.hexlify(self.to_bytes_32(int(seed)))
            else:
                self.privkey = sha256(seed)
            self.cprivkey = encode_privkey(self.privkey,'hex_compressed')
            self.pubkey = privtopub(self.privkey)
            self.cpubkey = encode_pubkey(self.pubkey,'hex_compressed')
            self.privkeywif = encode_privkey(self.privkey,'wif')
            self.cprivkeywif = encode_privkey(self.cprivkey,'wif_compressed')
            self.address = pubtoaddr(self.pubkey)
            self.caddress = pubtoaddr(self.cpubkey)
        
    def generate(self, event):
        '''Wrapper, creates keypair from text seed and updates displayed values.'''
        self.seed = self.seed_dialog()
        self.keypair_from_textseed(self.seed)
        self.update_output()

    def generate_from_file(self, event):
        '''Wrapper to create keypair from file seed and update displayed values.'''
        filenames,filepaths = self.file_dialog()
        if filenames == '': # user has cancelled
            pass
        else:
            self.keypair_from_fileseed(filenames,filepaths)
            self.update_output()

    def pil_to_image(self, pil):
        '''returns wx.Image from PIL'''
        image = wx.EmptyImage(pil.size[0], pil.size[1])
        new_image = pil.convert('RGB')
        data = new_image.tostring()
        image.SetData(data)
        return image

    def seed_dialog(self):
        '''Ask the user to browse input text to use as seed.'''
        dialog = wx.TextEntryDialog(None, "Input Seed", "Brainwallet Seed", "")
        answer = dialog.ShowModal()
        if answer == wx.ID_OK:
            self.seed = dialog.GetValue()
        dialog.Destroy()
        self.update_output() # probably not needed unless wx.ID_OK above
        return self.seed

    def file_dialog(self):
        '''
        Prompts user to browse to a file to use as seed.
        Stores filepath at self.seed
        '''
        # TODO handle != wx.ID_OK, other exceptions
        openFileDialog = wx.FileDialog(self, "Open File as Seed",
                                       "Brainwallet Seed", "",
                                       "All files (*.*)|*.*",
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)
        openFileDialog.ShowModal()
        filepaths = openFileDialog.GetPaths()
        filenames = openFileDialog.GetFilenames()
        openFileDialog.Destroy()
        return filenames,filepaths

    def multihash_dialog(self):
        '''Ask the user to input desired number of hash rounds.'''
        try:
            dialog = wx.TextEntryDialog(None, "Input number of rounds:",
                                        "Multihash Mode", "")
            answer = dialog.ShowModal()
            if answer == wx.ID_OK:
                self.multihash_numrounds = int(dialog.GetValue())
                dialog.Destroy()
            else:
                self.multihashCB.SetValue(False)
                self.multihash = False
        except ValueError:
            wx.MessageBox('Value Error: please input an integer.','Value Error')
            self.multihash_dialog()
        except Exception as e:
            self.exception_notice(e)
            self.multihash_dialog()

    def prng_dialog(self):
        try:
            dialog = wx.TextEntryDialog(None, "Number of words to return:",
                                        "Diceware PRNG Passphrase", "")
            answer = dialog.ShowModal()
            if answer == wx.ID_OK:
                numwords = int(dialog.GetValue())
                return numwords
        except ValueError:
            wx.MessageBox('Value Error: please input an integer.','Value Error')
            self.prng_dialog()
        except Exception as e:
            self.exception_notice(e)
            self.prng_dialog()

    def dice_dialog(self):
        try:
            dialog = wx.TextEntryDialog(None, messages.dicedialog,
                                        "Diceware Manual Rolls", "")
            answer = dialog.ShowModal()
            if answer == wx.ID_OK:
                rolls = dialog.GetValue()
                if ' ' in rolls:
                    rolls = rolls.replace(' ',',')
                if ',' in rolls:
                    rolls = [x.strip() for x in rolls.split(',')]
                else:
                    wx.MessageBox(messages.diceerror,'Input Error')
                    self.dice_dialog()
                for roll in rolls:
                    if len(roll) != 5:
                        wx.MessageBox(messages.dicelen,'Roll Error')
                return rolls
        except Exception as e:
            self.exception_notice(e)
            self.dice_dialog()        

    def bip38_dialog(self):
        '''Ask the user to input password for BIP0038 encryption'''
        try:
            dialog = wx.TextEntryDialog(None, "Enter Password",
                                        "BIP 38 Encryption", "")
            answer = dialog.ShowModal()
            if answer == wx.ID_OK:
                # typecast string for bip38, unicode error
                # NOTE: double check spec, utf-8 requirement?
                self.bip38pass = str(dialog.GetValue())
                dialog.Destroy()
            else:# user did not press ok, clear pass
                self.bip38pass = ''
        except Exception as e:
            self.exception_notice(e)
            self.bip38_dialog()

    def decrypt_privkey_dialog(self):
        dialog = wx.TextEntryDialog(None,"Encrypted Private Key",
                                    "BIP 38 Decryption","")
        if dialog.ShowModal() == wx.ID_OK:
            encprivkey = dialog.GetValue()
            dialog.Destroy()
            return encprivkey
        dialog.Destroy()

    def decrypt_passphrase_dialog(self):
        dialog = wx.TextEntryDialog(None,"Passphrase","BIP 38 Decryption","")
        if dialog.ShowModal() == wx.ID_OK:
            encpassphrase = dialog.GetValue()
            dialog.Destroy()
            return str(encpassphrase)
        dialog.Destroy()
        
    def encrypt_priv(self):
        if not self.bip38pass: # no pass, set checkbox state to False
            self.bip38CB.SetValue(False)
            self.bip38 = False
        else:
            if self.compressed:
                self.bip38priv = self.bip38_encrypt(self.cprivkey,
                                                    self.bip38pass)
            if not self.compressed:
                self.bip38priv = self.bip38_encrypt(self.privkey,
                                                    self.bip38pass)

    def save_note(self,event):
        '''Prompts user to save note to disk.'''
        saveFileDialog = wx.FileDialog(self, "Save As", "", "", 
                                       "PNG (*.png)",
                                       wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if saveFileDialog.ShowModal()==wx.ID_OK:
            self.note.SaveFile(saveFileDialog.GetPath(),wx.BITMAP_TYPE_PNG)
        saveFileDialog.Destroy()
            
    def failed_notice(self):
        '''Dialog, warns user that one or more validity tests have failed.'''
        failnotice = wx.MessageDialog(None,
                                      messages.test_failed,
                                      'Tests Failed!', wx.OK | wx.ICON_STOP)
        failnotice.ShowModal()
        failnotice.Destroy()

    def exception_notice(self,e):
        '''Dialog, warns user of exception.'''
        exceptionnotice = wx.MessageDialog(None,
                                           messages.exception %(e),
                                           'Encountered Exception',
                                           wx.OK | wx.ICON_ERROR)
        exceptionnotice.ShowModal()
        exceptionnotice.Destroy()
        
    def multihash_notice(self):
        '''Dialog, displays notice about multihash methods.'''
        failnotice = wx.MessageDialog(None,
                                      messages.multihash,
                                      'Multihash Notice',
                                      wx.OK | wx.ICON_INFORMATION)
        failnotice.ShowModal()
        failnotice.Destroy()
        self.multinotice = True
        
    def run_tests(self,event):
        '''
        Execute tests with hardcoded values stored as dicts in self.tests,
        comparing fresh output to known-good values.
        '''
        reset_multihash = False
        if self.multihash: # disable multihash mode for testing
            reset_multihash = True
            self.multihash = False
        try:
            for test in self.tests:
                self.tests_passed = self.verify_test(test)
                if self.tests_passed == 'Failed':
                    self.failed_notice()
                    break
            self.update_output()
        except Exception as e:
            self.tests_passed = 'Failed'
            self.update_output()
            self.exception_notice(e)
        if reset_multihash:
            self.multihash = True
            if self.filelast:
                self.determine_keys(self.fileseed)
            else:
                self.determine_keys(self.seed)
            self.update_output()
              
    def verify_test(self, params):
        '''
        Verify a single test.
        Expects dict containing seed, address, privkeywif.
        Returns string, "Failed" or "Passed".
        '''

        test = self.keypair_from_textseed(params.get('seed'))
        if test.get('address') == params.get('address'):
            if test.get('privkeywif') == params.get('privkey'):
                return 'Passed'
            else:
                return 'Failed'
        else:
            return 'Failed'

    def bip38_encrypt(self,privkey,passphrase):
        '''BIP0038 non-ec-multiply encryption. Returns BIP0038 encrypted privkey.'''
        privformat = get_privkey_format(privkey)
        if privformat in ['wif_compressed','hex_compressed']:
            compressed = True
            flagbyte = '\xe0'
            if privformat == 'wif_compressed':
                privkey = encode_privkey(privkey,'hex_compressed')
                privformat = get_privkey_format(privkey)
        if privformat in ['wif', 'hex']:
            compressed = False
            flagbyte = '\xc0'
        if privformat == 'wif':
            privkey = encode_privkey(privkey,'hex')
            privformat = get_privkey_format(privkey)
        pubkey = privtopub(privkey)
        addr = pubtoaddr(pubkey)
        addresshash = hashlib.sha256(hashlib.sha256(addr).digest()).digest()[0:4]
        key = scrypt.hash(passphrase, addresshash, 16384, 8, 8)
        derivedhalf1 = key[0:32]
        derivedhalf2 = key[32:64]
        aes = AES.new(derivedhalf2)
        encryptedhalf1 = aes.encrypt(binascii.unhexlify('%0.32x' % (long(privkey[0:32], 16) ^ long(binascii.hexlify(derivedhalf1[0:16]), 16))))
        encryptedhalf2 = aes.encrypt(binascii.unhexlify('%0.32x' % (long(privkey[32:64], 16) ^ long(binascii.hexlify(derivedhalf1[16:32]), 16))))
        encrypted_privkey = ('\x01\x42' + flagbyte + addresshash + encryptedhalf1 + encryptedhalf2)
        encrypted_privkey += hashlib.sha256(hashlib.sha256(encrypted_privkey).digest()).digest()[:4] # b58check for encrypted privkey
        return base58.b58encode(encrypted_privkey)

    def bip38_decrypt(self,encrypted_privkey,passphrase):
        '''BIP0038 non-ec-multiply decryption. Returns hex privkey.'''
        d = base58.b58decode(encrypted_privkey)
        d = d[2:]
        flagbyte = d[0:1]
        d = d[1:]
        # respect flagbyte, return correct pair
        if flagbyte == '\xc0':
            self.compressed = False
        if flagbyte == '\xe0':
            self.compressed = True
        addresshash = d[0:4]
        d = d[4:-4]
        key = scrypt.hash(passphrase,addresshash, 16384, 8, 8)
        derivedhalf1 = key[0:32]
        derivedhalf2 = key[32:64]
        encryptedhalf1 = d[0:16]
        encryptedhalf2 = d[16:32]
        aes = AES.new(derivedhalf2)
        decryptedhalf2 = aes.decrypt(encryptedhalf2)
        decryptedhalf1 = aes.decrypt(encryptedhalf1)
        priv = decryptedhalf1 + decryptedhalf2
        priv = binascii.unhexlify('%064x' % (long(binascii.hexlify(priv), 16) ^ long(binascii.hexlify(derivedhalf1), 16)))
        pub = privtopub(priv)
        if self.compressed:
            pub = encode_pubkey(pub,'hex_compressed')
        addr = pubtoaddr(pub)
        if hashlib.sha256(hashlib.sha256(addr).digest()).digest()[0:4] != addresshash:
            wx.MessageBox(messages.addresshash,
                          'Addresshash Error')
            # TODO: investigate
            #self.decrypt_priv(wx.PostEvent) # start over
        else:
            return priv

    def decrypt_priv(self,event):
        # get privkey/pass from user
        encprivkey = self.decrypt_privkey_dialog()
        if encprivkey: # continue
            passphrase = self.decrypt_passphrase_dialog()
            # decrypt privkey
            priv = self.bip38_decrypt(encprivkey,passphrase)
            # update key variants
            self.derive_from_priv(priv)
            self.seed = 'N/A' # checked in update_output
            # update flags and checkbox values
            self.bip38 = False
            self.bip38CB.SetValue(False)
            self.multihash = False
            self.multihashCB.SetValue(False)
            # set compressed CB
            if self.compressed:
                self.compressCB.SetValue(True)
            if not self.compressed:
                self.compressCB.SetValue(False)
        # build note from keypair
        self.update_output()

    def derive_from_priv(self,priv):
        '''Derive key variants from private key priv.'''
        self.privkey = encode_privkey(priv,'hex')
        if self.debug:
            print(get_privkey_format(priv))
        self.cprivkey = encode_privkey(self.privkey,'hex_compressed')
        self.pubkey = privtopub(self.privkey)
        self.cpubkey = encode_pubkey(self.pubkey,'hex_compressed')
        self.privkeywif = encode_privkey(self.privkey,'wif')
        self.cprivkeywif = encode_privkey(self.cprivkey,'wif_compressed')
        self.address = pubtoaddr(self.pubkey)
        self.caddress = pubtoaddr(self.cpubkey)

    def customQR(self, data, ver=1,
                 error=qrcode.constants.ERROR_CORRECT_Q,
                 padding=1, block_size=10, makefit=True):
        qr = qrcode.QRCode(ver, error, block_size, padding)
        qr.add_data(data)
        qr.make(fit=makefit)
        return qr.make_image()

    def overlayQR(self, base, QR, position):
        layer = Image.new('RGBA', base.size, (0,0,0,0))
        layer.paste(QR, position)
        return Image.composite(layer, base, layer)

    def overlay_text(self, img, position, text, fontsize=12):
        fonttype = os.path.join('resources',"ubuntu-mono-bold.ttf")
        font = ImageFont.truetype(fonttype,fontsize)
        draw = ImageDraw.Draw(img)
        draw.text((position),text,(42,42,42),font=font)
        draw = ImageDraw.Draw(img)
        return img

    def build_note(self, addr, privkey):
        if self.bip38:
            image = os.path.join('resources','note-blue.png')
        else:
            image = os.path.join('resources','note.png')
        base = Image.open(image)
        pubQR = self.customQR(addr,block_size=12)
        img = self.overlayQR(base,pubQR,(1310, 422))
        privQR = self.customQR(privkey,ver=6,padding=0,
                               error=qrcode.constants.ERROR_CORRECT_Q,
                               block_size=9,makefit=False)
        img = self.overlayQR(img,privQR,(80, 200))
        if self.bip38:
            img = self.overlay_text(img,(76,100),'Encrypted Private Key:',28)
            img = self.overlay_text(img,(76,128),privkey[:29],26)
            img = self.overlay_text(img,(76,156),privkey[29:],26)
        img = self.overlay_text(img,(1244,916),addr,28)
        url = 'blockchain.info/address/'+addr
        urlQR = self.customQR(url,ver=6,block_size=7,padding=0,
                              error=qrcode.constants.ERROR_CORRECT_L,
                              makefit=False)
        img = self.overlayQR(img,urlQR,(1388, 48))
        img = self.pil_to_image(img)
        imgsmall = img.Scale(580,310)
        self.note = img.ConvertToBitmap()
        self.displaynote = imgsmall.ConvertToBitmap()
        return self.note

    def refresh(self,event):
        '''Event wrapper for update_output()'''
        self.update_output()

    def close(self,event):
        '''Exits the application via self.Destroy()'''
        self.Destroy()

        
if __name__=='__main__':
    app=wx.PySimpleApp()
    try:
        frame=Brainwallet(parent=None,id=-1)
        frame.Show()
        app.MainLoop()
    finally:
        del app
        
