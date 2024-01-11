from pynicotine import slskmessages
from pynicotine.pluginsystem import BasePlugin
from pynicotine.config import config
#from pynicotine.userbrowse import UserBrowse

#def enable(plugins):
#    global PLUGIN
#    PLUGIN = Plugin(plugins)


#def disable(plugins):
#    global PLUGIN
#    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Autobahn"
    settings = {
        'ban_message': 'AUTOMATIC MESSAGE: You are not sharing enough and you were banned. You will be unbanned when you will contribute.',
        'warn_message': 'AUTOMATIC MESSAGE: Thanks for sharing over 10GB. If you share over 20GB I will remove 2 file limit allowing you to queue as many files as you want',
        'friend_message': 'AUTOMATIC MESSAGE: Welcome to my buddy list. 2 file limit will no longer apply to you - you will need to retry all files stopped by the limit.\nAUTOMATIC MESSAGE: I would appreciate if you don\'t put more than 1000 files in a queue at a time as it may crash Nicotine+',
        'ban_min_files': 100,
        'ban_min_bytes': 10000,
        'friend_min_bytes': 20000
    }
    metasettings = {
        'ban_message': {
            'description': 'Banned message',
            'type': 'textview'},
        'warn_message': {
            'description': 'Warning message',
            'type': 'textview'},
        'friend_message': {
            'description': 'Added to list message',
            'type': 'textview'},
        'ban_min_files': {
            'description': 'Minimum number of shared files to avoid a ban',
            'type': 'integer'},
        'ban_min_bytes': {
            'description': 'Minimum total size of shared files to avoid a ban (MB)',
            'type': 'integer'},
        'friend_min_bytes': {
            'description': 'Minimum total size of shared files to add to friend list (MB)',
            'type': 'integer'}
    }

    def init(self):
        self.probed = {}
        self.retries = {}

    def upload_queued_notification(self, user, virtualfile, realfile):
        try:
            self.probed[user]
        except KeyError:
            self.probed[user] = 'requesting'
            self.retries[user] = 1
            self.frame.np.userbrowse.browse_user(user)
            self.core.queue.append(slskmessages.GetUserStats(user))
            self.log('User %s, requesting information...' % user)

    def user_stats_notification(self, user, stats):
        try:
            status = self.probed[user]
        except KeyError:
            # we did not trigger this notification
            return
        if status == 'requesting':
            #check if user file list has finished loading
            #if not ready - request UserStats again - it is used as a timer hack to prevent locking UI
            
            #status check fails if user browse tab is closed manualy before fully loading
            try:
                total_size_text = self.frame.userbrowse.pages[user].share_size_label.get_text()
                total_folders_text_temp = self.frame.userbrowse.pages[user].num_folders_label.get_text()
                total_folders_text = total_folders_text_temp.replace(",","")
                info_box_text = self.frame.userbrowse.pages[user].info_bar.label.get_text()
                progressbar_fraction = self.frame.userbrowse.pages[user].progress_bar.get_fraction()
                
                self.log("total %s, folders %s, progress %s, info_text %s" % (total_size_text, total_folders_text, progressbar_fraction, info_box_text))
                
                refreshing = True

                total_size_array = total_size_text.split(" ")
                total_size_number = float(total_size_array[0])
                total_size_unit = total_size_array[1]

                if (progressbar_fraction == 1):
                    self.log("fraction true");

                if ("empty" in info_box_text):
                    self.log("empty infobox true");
                    
                if (total_size_number > 0):
                    self.log("size >0 true");

                if (float(total_folders_text) > 0):
                    self.log("folders >0 true");

                if ((progressbar_fraction == 1) and ("offline" in info_box_text)):
                    refreshing = False

                if ((progressbar_fraction == 1) and ("empty" in info_box_text)):
                    refreshing = False
                
#                if ((progressbar_fraction == 1) and ((total_size_text != "0.0 B") or (total_folders_text != "0"))):
                if ((progressbar_fraction == 1) and ((total_size_number > 0) or (float(total_folders_text) > 0))):
                    refreshing = False

            except KeyError:
                return

            
            if refreshing:
                self.retries[user] = self.retries[user] + 1
                #user browse sometimes gets stuck - so every 100 tries (roughly 5-10s) new request will be made to push it
                if (self.retries[user] % 100 == 0):
                    self.log("Still waiting for files from user %s, retry %s" % (user, self.retries[user]))
                    self.core.userbrowse.browse_user(user)
                self.core.queue.append(slskmessages.GetUserStats(user))
                return

            #if cannot connect message appeared - stop checking
            info_box_text = self.frame.userbrowse.pages[user].info_bar.label.get_text()
            if ("offline" in info_box_text):
                return

            total_size_text = self.frame.userbrowse.pages[user].share_size_label.get_text()
            total_folders_text = self.frame.userbrowse.pages[user].num_folders_label.get_text()

            total_size_array = total_size_text.split(" ")
            total_size_number = float(total_size_array[0])
            total_size_unit = total_size_array[1]
            #self.log("after split %s, %s" % (total_size_number, total_size_unit))
            if (total_size_unit == "B"):
                total_size = total_size_number
            elif (total_size_unit == "KiB"):
                total_size = total_size_number * 1024
            elif (total_size_unit == "MiB"):
                total_size = total_size_number * 1024 * 1024
            elif (total_size_unit == "GiB"):
                total_size = total_size_number * 1024 * 1024 * 1024
            elif (total_size_unit == "TiB"):
                total_size = total_size_number * 1024 * 1024 * 1024 * 1024
            elif (total_size_unit == "PiB"):
                total_size = total_size_number * 1024 * 1024 * 1024 * 1024 * 1024
            elif (total_size_unit == "EiB"):
                total_size = total_size_number * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
            elif (total_size_unit == "ZiB"):
                total_size = total_size_number * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
            elif (total_size_unit == "YiB"):
                total_size = total_size_number * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
            else:
                total_size = 0

                    
            #total_size, num_folders = self.frame.userbrowse.pages[user].create_folder_tree(self.frame.userbrowse.pages[user].shares)
            total_size = int(total_size / 10000) / 100

            #check if user is on the buddy list already
            user_buddy = False
            for users in config.sections["server"]["userlist"]:
               if user == users[0]:
                   user_buddy = True

            ban = False
            add_to_list = False
            remove_from_list = False
            warn = False

            #decision matrix
            #there is a bug in Slsk client where it doesn't update shared files correctly and they are reported as 0
            #thus 0 may actually mean user is sharing - and usually a lot
            #                     < ban_min_bytes         ban_min_bytes - friend_min_bytes    > friend_min_bytes
            # 0                   ban / remove_from_list  warn / remove_from_list                    add_to_list
            # 1 - ban_min_files   ban / remove_from_list  ban / remove_from_list              ban / remove_from_list
            # > ban_min_files     ban / remove_from_list  warn / remove_from_list                    add_to_list

            #decision logic
            if ((stats['files'] > 0) and (stats['files'] < self.settings['ban_min_files'])):
#            if ((float(total_folders_text) > 0) and (stats['files'] < self.settings['ban_min_files'])):
                #user shares between 1 and ban_min_files 
                #ban user
                #self.log("1-100, ban & remove")
                self.log("User %s shares: %s / %s files, %s total Mbytes" % (user, stats['files'], self.settings['ban_min_files'], total_size))
                ban = True
                remove_from_list = True

            if (total_size < (self.settings['ban_min_bytes'])):
#            if (total_size < (self.settings['ban_min_bytes']) and total_size > 0):
                #user shares below ban_min_bytes
                #ban user
                #self.log("<10GB, ban & remove")
                self.log("User %s shares: %s / %s files, %s / %s / %s total Mbytes" % (user, stats['files'], self.settings['ban_min_files'], total_size, self.settings['ban_min_bytes'], self.settings['friend_min_bytes']))
                ban = True
                remove_from_list = True

            if (((total_size > (self.settings['ban_min_bytes'])) and (total_size < (self.settings['friend_min_bytes'])))
                    and ((stats['files'] > self.settings['ban_min_files']) or (stats['files'] == 0))):
                #user shares enough 
                #self.log("0/100+, 10-20GB, remove")
                self.log("User %s shares: %s / %s files, %s / %s / %s total Mbytes" % (user, stats['files'], self.settings['ban_min_files'], self.settings['ban_min_bytes'], total_size, self.settings['friend_min_bytes']))
                remove_from_list = True
                warn = True

            if ((total_size > (self.settings['friend_min_bytes']))
                    and ((stats['files'] > self.settings['ban_min_files']) or (stats['files'] == 0))):
                #add user
                #self.log("0/100+, 20GB+, add")
                self.log("User %s shares: %s / %s files, %s / %s / %s total Mbytes" % (user, stats['files'], self.settings['ban_min_files'], self.settings['ban_min_bytes'], self.settings['friend_min_bytes'], total_size))
                add_to_list = True

            #actions
            if ban:
                #ban user
                self.frame.np.network_filter.ban_user(user)
                self.log("User banned: %s" %user)
                #Send message to user
                for line in self.settings['ban_message'].splitlines():
                    self.send_private(user, line)

            if warn:
                #warn user
                self.log("User warned: %s" %user)
                #Send message to user
                for line in self.settings['warn_message'].splitlines():
                    self.send_private(user, line)

            if add_to_list:
                #add user to list if not yet there
                if not user_buddy:
                    self.frame.np.userlist.add_user(user)
                    self.log("User added to friend list: %s" %user)
                    for line in self.settings['friend_message'].splitlines():
                        self.send_private(user, line)
                else:
                    self.log("User already on friend list: %s" %user)
                    
            if remove_from_list:
                #remove from list
                if user_buddy:
                    self.frame.np.userlist.remove_user(user)
                    self.log("User removed from friend list: %s" %user)

            #done with this user :)
            self.probed[user] = 'processed'
        else:
            # We already dealt with this user.
            pass
