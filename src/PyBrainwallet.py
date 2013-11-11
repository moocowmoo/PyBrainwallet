import wx
import pybitcointools # github.com/vbuterin/pybitcointools
import qrcode

#############################################################################
## This work is free. You can redistribute it and/or modify it under the    #
## terms of the Do What The Fuck You Want To Public License, Version 2,     #
## as published by Sam Hocevar. See http://www.wtfpl.net/ for more details. #
#############################################################################

## TODO:
# Display compressed address/WIF
# Diceware word lookup and optional passphrase generation
# Binaries for Linux/other?
# BIP0038 encrypt/decrypt - please notify author of Python implementation
# Note generation

version = '0.33'


class Brainwallet(wx.Frame):

    def __init__(self,parent,id):
        
        wx.Frame.__init__(self,parent,id,
                         'PyBrainwallet',
                         size=(580,320))

        # Panel and Buttons
        panel=wx.Panel(self)
        
        multihashCB = wx.CheckBox(panel, -1, "Multihash", (22, 215), (-1, -1))
        
        gen_button=wx.Button(panel,
                                 label='From Text',
                                 pos=(20,170),
                                 size=(70,20))
        
        gen_file_button=wx.Button(panel,
                                 label='From File',
                                 pos=(20,190),
                                 size=(70,20))
        
        copy_public_button=wx.Button(panel,
                               label='Copy Address',
                               pos=(110,170),
                               size=(75,20))
        
        copy_private_button=wx.Button(panel,
                               label='Copy Privkey',
                               pos=(110,190),
                               size=(75,20))
        
        test_button=wx.Button(panel,
                              label='Tests',
                              pos=(205,170),
                              size=(70,20))
        
        close_button=wx.Button(panel,
                               label='Exit',
                               pos=(205,190),
                               size=(70,20))

        self.Bind(wx.EVT_CHECKBOX, self.set_multihash, multihashCB)
        self.Bind(wx.EVT_BUTTON,self.generate,gen_button)
        self.Bind(wx.EVT_BUTTON,self.generate_from_file,gen_file_button)
        self.Bind(wx.EVT_BUTTON,self.close,close_button)
        self.Bind(wx.EVT_BUTTON,self.run_tests,test_button)
        self.Bind(wx.EVT_BUTTON,self.copy_public,copy_public_button)
        self.Bind(wx.EVT_BUTTON,self.copy_private,copy_private_button)
        self.Bind(wx.EVT_CLOSE,self.close)

        # Menu and Statusbar
        status=self.CreateStatusBar()
        menubar=wx.MenuBar()
        file_menu=wx.Menu()
        options_menu=wx.Menu()
        about_menu=wx.Menu()
        
        menubar.Append(file_menu,'File')
        menu_save_keypair=file_menu.Append(wx.NewId(),'Save Keypair','Not yet implemented; use the copy buttons provided to save keys.')
        self.Bind(wx.EVT_MENU,self.keypair_to_file,menu_save_keypair)
        
        menubar.Append(options_menu,'Options')
        menu_refresh=options_menu.Append(wx.NewId(),'Refresh','Force refresh')
        self.Bind(wx.EVT_MENU,self.refresh,menu_refresh)
        
        menubar.Append(about_menu,'About')
        menu_about_about=about_menu.Append(wx.NewId(),'About','PyBrainwallet version %s' % (version))
        self.Bind(wx.EVT_MENU,self.on_about,menu_about_about)
        
        menu_about_license=about_menu.Append(wx.NewId(),'License','Do What The Fuck You Want To Public License, Version 2')
        self.Bind(wx.EVT_MENU,self.on_license,menu_about_license)
        
        menu_about_security=about_menu.Append(wx.NewId(),'Security','Basic security guidelines')
        self.Bind(wx.EVT_MENU,self.on_security,menu_about_security)
        
        self.SetMenuBar(menubar)

        # initial display values
        self.seed = 'correct horse battery staple'
        self.address = '1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T'
        self.privkeywif = '5KJvsngHeMpm884wtkJNzQGaCErckhHJBGFsvd3VyK5qMZXj3hS'
        self.tests_passed = 'Untested'
        
        # flags
        self.multinotice = False
        self.multihash = False
        self.filelast = False

        # text fields
        self.test_static=wx.StaticText(panel,-1,'Tests:',(5,7),(200,-1),wx.ALIGN_LEFT)
        self.test_text=wx.TextCtrl(self, value=self.tests_passed,pos=(44,5), size=(60,-1), style=wx.TE_RICH|wx.TE_CENTRE)
        
        self.seed_static=wx.StaticText(panel,-1,'Seed:',(5,32),(200,-1),wx.ALIGN_LEFT)
        self.seed_text=wx.TextCtrl(self, value=self.seed, pos=(44,30), size=(510,-1))
        
        self.address_static=wx.StaticText(panel,-1,'Address:',(106,60),(200,-1),wx.ALIGN_LEFT)
        self.address_text=wx.TextCtrl(self, value=self.address,pos=(105,80), size=(220,-1),style=wx.TE_CENTRE)
        
        self.privkeywif_static=wx.StaticText(panel,-1,'Privkey (WIF):',(380,114),(200,-1),wx.ALIGN_LEFT)
        self.privkeywif_text=wx.TextCtrl(self, value=self.privkeywif,pos=(135,134), size=(320,-1),style=wx.TE_CENTRE)
        
        # QR codes
        self.pubQR = wx.StaticBitmap(self, pos=(5,60),size=(100,100))
        self.privQR = wx.StaticBitmap(self, pos=(460,60),size=(100,100))

        # make sure everything is loaded
        self.update_output()

        # test values created with brainwallet.org
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


    def set_multihash(self, event):
        self.multihash = event.IsChecked()
        if not self.multinotice:
            self.multihash_notice()
        if event.IsChecked():
            self.multihash_dialog()
        # regen keys and display
        if self.filelast:
            self.determine_keys(self.fileseed)
        else:
            self.determine_keys(self.seed)
        self.update_output()

    def on_about(self,event):
        '''Dialog triggered by About option in About menu.'''
        aboutnotice = wx.MessageDialog(None,
                                'PyBrainwallet is an attempt to re-create the basic functions of brainwallet.org. The program generates and displays a keypair based on the SHA256 hash of seed text, or a file. With it, you can create a keypair that is easy to recover using your memory. \n\nBrainwallets are very handy in many ways, but may not be suitable for all use cases. You may prefer to import your complete keypair into a wallet, offering an easy method to recover the keys in the event of wallet destruction or lockout. Some wallets also allow an address to be treated as "watching only", not requiring the private key until funds are to be spent. Another use case is a non-file "cold" wallet, not used in any active wallet, but ready to be recalled when needed. In this case, the private key must be imported or swept to a new addres to spend. \n\nIf used correctly, brainwallets can be a powerful tool, potentially protecting your keys from accidental or intentional destruction. However, users need to be aware of the increased security requirements, the threats that exist, and how those threats will evolve. \n\nAs with many things in the Bitcoin world, brainwallet security is placed squarely on the shoulders of the user. With that in mind, verify the validity of keys you generate, and employ trustless security wherever possible.  \n\nFor more, view the Security entry in the About menu.',
                                'About PyBrainwallet', wx.OK | wx.ICON_INFORMATION)
        aboutnotice.ShowModal()
        aboutnotice.Destroy()
        
    def on_security(self, event):
        '''Dialog triggered by Security option in About menu.'''
        secnotice = wx.MessageDialog(None,
                                '\n\nThe standard Bitcoin threat model applies. Bitcoin-strong passphrases, non-common or public files (i.e. don\'t use a profile photo), and an offline live or stateless OS are recommended. \n\nBrainwallets require a high degree of entropy in order to be considered secure for any period of time. Brainwallet brute-forcing is a hobby for many bright individuals with powerful hardware at their disposal. Use of weak seeds, or common/publicly available files WILL eventually lead to loss. Diceware (https://en.wikipedia.org/wiki/Diceware) and a large number of words is recommended at a minimum. \n\nUse of files is considered a novelty, and not recommended in most circumstances. If you must use a file, be sure it is unique, and that you control the only copies. \n\nFor more on brainwallets and best practices, see https://en.bitcoin.it/wiki/Brainwallet \n\nThough an effort is made to ensure the program produces valid output, it is up to the user to verify keys before storing coins. \n\nAuthor is not responsible for lost or stolen coins, under any circumstances.',
                                'Security', wx.OK | wx.ICON_INFORMATION)
        secnotice.ShowModal()
        secnotice.Destroy()

    def on_license(self,event):
        '''Dialog triggered by License option in About menu.'''
        licensenotice = wx.MessageDialog(None,
                               'Author is not responsible for malfunction, fire, loss, explosions, or change in mood or personality. Some features are experimental and may break, cause issues, or be removed in future versions. \n\nPyBrainwallet is licensed under the WTFPL, version 2. \nFor a copy of the license, visit www.wtfpl.net/txt/copying/, or view the PyBrainwallet source.',
                               'PyBrainwallet License', wx.OK | wx.ICON_INFORMATION)
        licensenotice.ShowModal()
        licensenotice.Destroy()

    def copy_public(self,event):
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
        self.address_text.SetValue(self.address)
        self.privkeywif_text.SetValue(self.privkeywif)
        self.show_privQR()
        self.show_pubQR()
        if self.tests_passed == 'Passed':
            self.test_text.SetForegroundColour((0,180,42))
        elif self.tests_passed == 'Failed':
            self.test_text.SetForegroundColour(wx.BLACK)
            self.test_text.SetBackgroundColour(wx.RED)

    def address_from_privkey(self, privkey):
        '''Returns address derived from privkey, as string.'''
        return pybitcointools.privtopub(privkey)

    def privkey_from_seed(self, seed):
        '''Returns privkey as int, via sha256 hash of given seed.'''
        return pybitcointools.sha256(seed)
        
    def keypair_from_textseed(self, seed):
        self.filelast = False
        '''Generate a keypair from text seed. Returns dict.'''
        self.seed = seed
        self.determine_keys(seed)
        # TODO return all values in dict and test
        return {'privkeywif':self.privkeywif,
                'address':self.address}

    def keypair_from_fileseed(self, filelist, filepaths):
        self.filelast = True
        '''Generate a keypair from list of file(s). Returns dict.'''
        # store the filename(s) in self.seed for display
        self.seed = ''
        for filename in filelist:
            self.seed += filename+', '
        self.seed = self.seed[:-2] # strip trailing
        self.fileseed = ''
        if len(filepaths) == 1: 
            self.fileseed = file(filepaths[0],'rb+').read()
        else:
            for filepath in filepaths:
                self.fileseed += file(filepath,'rb+').read()
                len(self.fileseed)
        self.determine_keys(self.fileseed)
        # TODO return all values in dict and test
        return {'privkeywif':self.privkeywif,
                'address':self.address}

    def determine_keys(self, seed):
        if self.multihash:
            for i in range(1,self.multihash_numrounds):
                seed = pybitcointools.sha256(seed)
        self.privkey = pybitcointools.sha256(seed)
        self.cprivkey = pybitcointools.encode_privkey(self.privkey,'hex_compressed')
        self.pubkey = pybitcointools.privtopub(self.privkey)
        self.cpubkey = pybitcointools.encode_pubkey(self.pubkey,'hex_compressed')
        self.privkeywif = pybitcointools.encode_privkey(self.privkey,'wif')
        self.cprivkeywif = pybitcointools.encode_privkey(self.cprivkey,'wif_compressed')
        self.address = pybitcointools.pubtoaddr(self.pubkey)
        self.caddress = pybitcointools.pubtoaddr(self.cpubkey)
        

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

    def genQR(self,data):
        '''Returns QR representing input data as PIL.'''
        qr = qrcode.QRCode(version=4,
                           error_correction=qrcode.constants.ERROR_CORRECT_L,
                           border=1,
                           box_size=1)
        qr.add_data(data)
        qr.make(fit=False)
        img = qr.make_image()
        return img

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
        self.update_output()
        return self.seed

    def file_dialog(self):
        '''
        Prompts user to browse to a file to use as seed. Stores filepath at self.seed
        and returns only if non-empty.
        '''
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
        '''Ask the user to input desired number of hash rounds'''
        try:
            dialog = wx.TextEntryDialog(None, "Multihash Rounds", "Input number of rounds:", "")
            answer = dialog.ShowModal()
            if answer == wx.ID_OK:
                self.multihash_numrounds = int(dialog.GetValue())
                dialog.Destroy()
        except ValueError:
            wx.MessageBox('Value Error: please input an integer.','Value Error')
            self.multihash_dialog()
        except Exception as e:
            self.exception_notice(e)
            self.multihash_dialog()

    def keypair_to_file():
        # TODO implement note generation
        # TODO BIP38 encryption
        pass
            
    def failed_notice(self):
        '''Dialog, warns user that one or more output validity tests have failed.'''
        failnotice = wx.MessageDialog(None,
                                      'One or more verification tests failed. Output should not be trusted without validating.',
                                      'Tests Failed!', wx.OK | wx.ICON_STOP)
        failnotice.ShowModal()
        failnotice.Destroy()

    def exception_notice(self,e):
        '''Dialog, warns user of exception.'''
        failnotice = wx.MessageDialog(None,
                                      'PyBrainWallet has encounted an exception:\n%s\n\nTo report this issue, visit github.com/nomorecoin/PyBrainwallet/issues' %(e),
                                      'Encountered Exception', wx.OK | wx.ICON_ERROR)
        failnotice.ShowModal()
        failnotice.Destroy()
        
    def multihash_notice(self):
        '''Dialog, displays notice about multihash methods.'''
        failnotice = wx.MessageDialog(None,
                                      'This mode is experimental, and is not likely to be supported by other tools.\n\nMultihash mode asks you to input a number, and hashes your seed the desired number of rounds. Consider this akin to a PIN number, and do not forget it, as it is needed to recover your wallet.',
                                      'Multihash Notice', wx.OK | wx.ICON_INFORMATION)
        failnotice.ShowModal()
        failnotice.Destroy()
        self.multinotice = True
        
    def run_tests(self,event):
        '''
        Execute tests with hardcoded values stored as list dicts in self.tests,
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
        if reset_multihash: # re-enable multihash
            self.multihash = True
            if self.filelast:
                self.determine_keys(self.fileseed)
            else:
                self.determine_keys(self.seed)
            self.update_output()
              
    def verify_test(self, params):
        '''
        Verify the output of a single test. Expects dict containing seed, address, privkeywif.
        Returns "Failed" or "Passed".
        '''
        # TODO expand tests to all possible key values (compressed, etc)
        # TODO determine method of testing fileseeds
        test = self.keypair_from_textseed(params.get('seed'))
        if test.get('address') == params.get('address'):
            if test.get('privkeywif') == params.get('privkey'):
                return 'Passed'
            else:
                return 'Failed'
        else:
            return 'Failed'
    
    def show_privQR(self):
        '''Generates and updates privkey QR image in main panel.'''
        image = self.genQR(self.privkeywif)
        image = self.pil_to_image(image)
        image = image.Scale(96,96)
        image = image.ConvertToBitmap()
        self.privQR.SetBitmap(image)
        
    def show_pubQR(self):
        '''Generates and updates address QR image in main panel.'''
        image = self.genQR(self.address)
        image = self.pil_to_image(image)
        image = image.Scale(96,96)
        image = image.ConvertToBitmap()
        self.pubQR.SetBitmap(image)

    def constrain_image(self,img):
        return img.Scale(96,96)
    
    def refresh(self,event):
        '''Event wrapper for update_output()'''
        self.update_output()

    def close(self,event):
        '''Exits the application via self.Destroy()'''
        self.Destroy()

        
if __name__=='__main__':
    app=wx.PySimpleApp()
    frame=Brainwallet(parent=None,id=-1)
    frame.Show()
    app.MainLoop()
        
