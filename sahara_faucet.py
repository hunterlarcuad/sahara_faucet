import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
import math
from datetime import datetime, timedelta


from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from DrissionPage._elements.none_element import NoneElement
# from DrissionPage.common import Keys
# from DrissionPage import Chromium
# from DrissionPage.common import Actions
# from DrissionPage.common import Settings

from fun_utils import ding_msg
from fun_utils import get_date
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import format_ts
from fun_utils import time_difference
# from fun_utils import extract_numbers
from fun_utils import seconds_to_hms

from auto_utils import get_window_size
# from auto_utils import auto_click

from conf import DEF_LOCAL_PORT
from conf import DEF_INCOGNITO
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_NUM_TRY
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_BROWSER
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS
from conf import DEF_OKX_EXTENSION_PATH
from conf import EXTENSION_ID_OKX

from conf import DEF_CAPMONSTER_EXTENSION_PATH
from conf import EXTENSION_ID_CAPMONSTER
from conf import DEF_CAPMONSTER_KEY

from conf import DEF_PWD

from conf import DEF_PATH_DATA_PURSE
from conf import DEF_HEADER_PURSE

from conf import TZ_OFFSET
from conf import DEL_PROFILE_DIR

from conf import logger

"""
2025.02.16
saharalabs faucet
"""

DEF_URL_FAUCET = 'https://faucet.saharalabs.ai/'

# output
FIELD_NUM = 2
IDX_ACCOUNT = 0
IDX_UPDATE = -1


class FaucetTask():
    def __init__(self) -> None:
        self.args = None
        self.page = None
        self.s_today = get_date(is_utc=True)
        self.file_proxy = None

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}

        self.dic_purse = {}

        self.purse_load()

    def set_args(self, args):
        self.args = args
        self.is_update = False

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

    def __del__(self):
        self.status_save()

    def purse_load(self):
        self.file_purse = f'{DEF_PATH_DATA_PURSE}/purse.csv'
        self.dic_purse = load_file(
            file_in=self.file_purse,
            idx_key=0,
            header=DEF_HEADER_PURSE
        )

    def status_load(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def get_status_by_idx(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        s_val = ''
        lst_pre = self.dic_status.get(s_profile, [])
        if len(lst_pre) == FIELD_NUM:
            try:
                s_val = int(lst_pre[idx_status])
            except: # noqa
                pass

        return s_val

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.page:
                try:
                    self.page.quit()
                except Exception as e: # noqa
                    # logger.info(f'[Close] Error: {e}')
                    pass

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        # Settings.singleton_tab_obj = True

        profile_path = s_profile

        # 是否设置无痕模式
        if DEF_INCOGNITO:
            co = ChromiumOptions().incognito(True)
        else:
            co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)
        # co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') # noqa

        co.set_argument('--accept-lang', 'en-US')  # 设置语言为英语（美国）
        co.set_argument('--lang', 'en-US')

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        # 关闭沙盒模式
        # co.set_argument('--no-sandbox')

        # popups支持的取值
        # 0：允许所有弹窗
        # 1：只允许由用户操作触发的弹窗
        # 2：禁止所有弹窗
        # co.set_pref(arg='profile.default_content_settings.popups', value='0')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        self.load_extension(co, DEF_OKX_EXTENSION_PATH)
        self.load_extension(co, DEF_CAPMONSTER_EXTENSION_PATH)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa

        try:
            self.page = ChromiumPage(co)
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

        self.page.wait.load_start()
        # self.page.wait(2)

        self.init_capmonster()

    def load_extension(self, co, extersion_path):
        # 获取当前工作目录
        current_directory = os.getcwd()

        # 检查目录是否存在
        if os.path.exists(os.path.join(current_directory, extersion_path)): # noqa
            self.logit(None, f'okx plugin path: {extersion_path}')
            co.add_extension(extersion_path)
        else:
            self.logit(None, f'{extersion_path} plugin directory is not exist. Exit!') # noqa
            sys.exit(1)

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def set_window_size(self):
        # 获取主屏分辨率
        screen_width, screen_height = get_window_size()

        # 计算一半的分辨率
        half_width = screen_width // 2

        # 设置窗口大小为主屏的一半
        self.page.set.window.size(half_width, screen_height)

        # 设置窗口位置为靠右，即主屏宽度减去一半宽度
        self.page.set.window.location(screen_width - half_width, 0)

    def close_popup_tabs(self, s_keep='OKX Web3'):
        # 关闭 OKX 弹窗
        if len(self.page.tab_ids) > 1:
            self.logit('close_popup_tabs', None)
            n_width_max = -1
            for tab_id in self.page.tab_ids:
                n_width_tab = self.page.get_tab(tab_id).rect.size[0]
                if n_width_max < n_width_tab:
                    n_width_max = n_width_tab

            tab_ids = self.page.tab_ids
            n_tabs = len(tab_ids)
            for i in range(n_tabs-1, -1, -1):
                tab_id = tab_ids[i]
                n_width_tab = self.page.get_tab(tab_id).rect.size[0]
                if n_width_tab < n_width_max:
                    s_title = self.page.get_tab(tab_id).title
                    self.logit(None, f'Close tab:{s_title} width={n_width_tab} < {n_width_max}') # noqa
                    self.page.get_tab(tab_id).close()
                    return True

        self.set_window_size()
        return False

    def is_exist(self, s_title, s_find, match_type):
        b_ret = False
        if match_type == 'fuzzy':
            if s_title.find(s_find) >= 0:
                b_ret = True
        else:
            if s_title == s_find:
                b_ret = True

        return b_ret

    def check_start_tabs(self, s_keep='新标签页', match_type='fuzzy'):
        """
        关闭多余的标签页
        match_type
            precise 精确匹配
            fuzzy 模糊匹配
        """
        if self.page.tabs_count > 1:
            self.logit('check_start_tabs', None)
            tab_ids = self.page.tab_ids
            n_tabs = len(tab_ids)
            for i in range(n_tabs-1, -1, -1):
                tab_id = tab_ids[i]
                s_title = self.page.get_tab(tab_id).title
                # print(f's_title={s_title}')
                if self.is_exist(s_title, s_keep, match_type):
                    continue
                if len(self.page.tab_ids) == 1:
                    break
                self.logit(None, f'Close tab:{s_title}')
                self.page.get_tab(tab_id).close()
            self.logit(None, f'Keeped tab: {self.page.title}')
            return True
        return False

    def init_capmonster(self):
        """
        chrome-extension://jiofmdifioeejeilfkpegipdjiopiekl/popup/index.html
        """
        s_url = f'chrome-extension://{EXTENSION_ID_CAPMONSTER}/popup.html'
        self.page.get(s_url)
        # self.page.wait.load_start()
        self.page.wait(3)

        def get_balance():
            """
            Balance: $0.9987
            Balance: Wrong key
            """
            self.page.wait(1)
            ele_info = self.page.ele('tag:div@@class=sc-bdvvtL dTzMWc', timeout=2) # noqa
            if not isinstance(ele_info, NoneElement):
                s_info = ele_info.text
                logger.info(f'{s_info}')
                self.logit('init_capmonster', f'CapMonster {s_info}')
                if s_info.find('$') >= 0:
                    return True
                if s_info.find('Wrong key') >= 0:
                    return False
            return False

        def click_checkbox(s_value):
            ele_input = self.page.ele(f'tag:input@@value={s_value}', timeout=2)
            if not isinstance(ele_input, NoneElement):
                if ele_input.states.is_checked is True:
                    ele_input.click(by_js=True)
                    self.logit(None, f'cancel checkbox {s_value}')
                    return True
            return False

        def cancel_checkbox():
            lst_text = [
                'ReCaptcha2',
                'ReCaptcha3',
                'ReCaptchaEnterprise',
                'GeeTest',
                'ImageToText',
                'BLS',
            ]
            for s_value in lst_text:
                click_checkbox(s_value)

        self.save_screenshot(name='capmonster_1.jpg')

        if get_balance():
            return True

        ele_block = self.page.ele('tag:div@@class=sc-bdvvtL ehUtQX', timeout=2)
        if isinstance(ele_block, NoneElement):
            self.logit('init_capmonster', 'API-key block is not found')
            return False
        self.logit('init_capmonster', None)

        ele_input = ele_block.ele('tag:input')
        if not isinstance(ele_input, NoneElement):
            if ele_input.value == DEF_CAPMONSTER_KEY:
                self.logit(None, 'init_capmonster has been initialized before')
                return True
            if len(ele_input.value) > 0 and ele_input.value != DEF_CAPMONSTER_KEY: # noqa
                ele_input.click.multi(times=2)
                ele_input.clear(by_js=True)
                # self.page.actions.type('BACKSPACE')
            self.page.actions.move_to(ele_input).click().type(DEF_CAPMONSTER_KEY) # noqa
            self.page.wait(1)
            ele_btn = ele_block.ele('tag:button')
            if not isinstance(ele_btn, NoneElement):
                if ele_btn.states.is_enabled is False:
                    self.logit(None, 'The Save Button is_enabled=False')
                else:
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                    self.logit(None, 'Saved capmonster_key [OK]')
                    cancel_checkbox()
                    if get_balance():
                        return True
            else:
                self.logit(None, 'the save button is not found')
                return False
        else:
            self.logit(None, 'the input element is not found')
            return False

        logger.info('capmonster init success')
        self.save_screenshot(name='capmonster_2.jpg')

    def okx_secure_wallet(self):
        # Secure your wallet
        ele_info = self.page.ele('Secure your wallet')
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_secure_wallet', 'Secure your wallet')
            ele_btn = self.page.ele('Password', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)
                self.logit('okx_secure_wallet', 'Select Password')

                # Next
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                    self.logit('okx_secure_wallet', 'Click Next')
                    return True
        return False

    def okx_set_pwd(self):
        # Set password
        ele_info = self.page.ele('Set password', timeout=2)
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_set_pwd', 'Set Password')
            ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit('okx_set_pwd', 'Input Password')
                self.page.actions.move_to(ele_input).click().type(DEF_PWD)
            self.page.wait(1)
            ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Re-enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                self.logit('okx_set_pwd', 'Re-enter Password')
            self.page.wait(1)
            ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit('okx_set_pwd', 'Password Confirmed [OK]')
                return True
        return False

    def okx_bulk_import_private_key(self, s_key):
        ele_btn = self.page.ele('@@tag()=div@@class:_typography@@text():Bulk import private key', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            ele_btn.click(by_js=True)
            self.logit('okx_bulk_import_private_key', 'Click ...')

            self.page = self.page.get_tab(self.page.latest_tab.tab_id)

            ele_btn = self.page.ele('@@tag()=i@@id=okdDialogCloseBtn', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Close pwd input box ...')
                ele_btn.click(by_js=True)

            ele_btn = self.page.ele('@@tag()=div@@data-testid=okd-select-reference-value-box', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Select network ...')
                ele_btn.click(by_js=True)

            ele_btn = self.page.ele('@@tag()=div@@class:_typography@@text()=EVM networks', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Click EVM networks ...')
                ele_btn.click(by_js=True)

            ele_input = self.page.ele('@@tag()=textarea@@id:pk-input@@placeholder:private', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit(None, 'Click EVM networks ...')
                self.page.actions.move_to(ele_input).click().type(s_key) # noqa
                self.page.wait(5)

    def init_okx(self, is_bulk=False):
        """
        chrome-extension://jiofmdifioeejeilfkpegipdjiopiekl/popup/index.html
        """
        # self.check_start_tabs()
        s_url = f'chrome-extension://{EXTENSION_ID_OKX}/home.html'
        self.page.get(s_url)
        # self.page.wait.load_start()
        self.page.wait(3)
        self.close_popup_tabs()
        self.check_start_tabs('OKX Wallet', 'precise')

        self.logit('init_okx', f'tabs_count={self.page.tabs_count}')

        self.save_screenshot(name='okx_1.jpg')

        ele_info = self.page.ele('@@tag()=div@@class:balance', timeout=2) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.text
            self.logit('init_okx', f'Account balance: {s_info}') # noqa
            return True

        ele_btn = self.page.ele('Import wallet', timeout=2)
        if not isinstance(ele_btn, NoneElement):
            # Import wallet
            self.logit('init_okx', 'Import wallet ...')
            ele_btn.click(by_js=True)

            self.page.wait(1)
            ele_btn = self.page.ele('Seed phrase or private key', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                # Import wallet
                self.logit('init_okx', 'Select Seed phrase or private key ...') # noqa
                ele_btn.click(by_js=True)
                self.page.wait(1)

                s_key = self.dic_purse[self.args.s_profile][1]
                if len(s_key.split()) == 1:
                    # Private key
                    self.logit('init_okx', 'Import By Private key')
                    ele_btn = self.page.ele('Private key', timeout=2)
                    if not isinstance(ele_btn, NoneElement):
                        # 点击 Private key Button
                        self.logit('init_okx', 'Select Private key')
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                        ele_input = self.page.ele('@class:okui-input-input input-textarea ta', timeout=2) # noqa
                        if not isinstance(ele_input, NoneElement):
                            # 使用动作，输入完 Confirm 按钮才会变成可点击状态
                            self.page.actions.move_to(ele_input).click().type(s_key) # noqa
                            self.page.wait(5)
                            self.logit('init_okx', 'Input Private key')
                    is_bulk = True
                    if is_bulk:
                        self.okx_bulk_import_private_key(s_key)
                else:
                    # Seed phrase
                    self.logit('init_okx', 'Import By Seed phrase')
                    words = s_key.split()

                    # 输入助记词需要最大化窗口，否则最后几个单词可能无法输入
                    self.page.set.window.max()

                    ele_inputs = self.page.eles('.mnemonic-words-inputs__container__input', timeout=2) # noqa
                    if not isinstance(ele_inputs, NoneElement):
                        self.logit('init_okx', 'Input Seed phrase')
                        for i in range(len(ele_inputs)):
                            ele_input = ele_inputs[i]
                            self.page.actions.move_to(ele_input).click().type(words[i]) # noqa
                            self.logit(None, f'Input word [{i+1}/{len(words)}]') # noqa
                            self.page.wait(1)

                # Confirm
                max_wait_sec = 10
                i = 1
                while i < max_wait_sec:
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
                    self.logit('init_okx', f'To Confirm ... {i}/{max_wait_sec}') # noqa
                    if not isinstance(ele_btn, NoneElement):
                        if ele_btn.states.is_enabled is False:
                            self.logit(None, 'Confirm Button is_enabled=False')
                        else:
                            if ele_btn.states.is_clickable:
                                ele_btn.click(by_js=True)
                                self.logit('init_okx', 'Confirm Button is clicked') # noqa
                                self.page.wait(1)
                                break
                            else:
                                self.logit(None, 'Confirm Button is_clickable=False') # noqa

                    i += 1
                    self.page.wait(1)
                # 未点击 Confirm
                if i >= max_wait_sec:
                    self.logit('init_okx', 'Confirm Button is not found [ERROR]') # noqa

                # 导入私钥有此选择页面，导入助记词则没有此选择过程
                # Select network and Confirm
                ele_info = self.page.ele('Select network', timeout=2)
                if not isinstance(ele_info, NoneElement):
                    self.logit('init_okx', 'Select network ...')
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                        self.logit('init_okx', 'Select network finish')

                self.okx_secure_wallet()

                # Set password
                is_success = self.okx_set_pwd()

                # Start your Web3 journey
                self.page.wait(1)
                self.save_screenshot(name='okx_2.jpg')
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Start', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.logit('init_okx', 'import wallet success')
                    self.save_screenshot(name='okx_3.jpg')
                    self.page.wait(2)

                if is_success:
                    return True
        else:
            ele_info = self.page.ele('Your portal to Web3', timeout=2)
            if not isinstance(ele_info, NoneElement):
                self.logit('init_okx', 'Input password to unlock ...')
                s_path = '@@tag()=input@@data-testid=okd-input@@placeholder:Enter' # noqa
                ele_input = self.page.ele(s_path, timeout=2) # noqa
                if not isinstance(ele_input, NoneElement):
                    self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                    if ele_input.value != DEF_PWD:
                        self.logit('init_okx', '[ERROR] Fail to input passwrod !') # noqa
                        self.page.set.window.max()
                        return False

                    self.page.wait(1)
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Unlock', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)

                        self.logit('init_okx', 'login success')
                        self.save_screenshot(name='okx_2.jpg')

                        return True
            else:
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                else:
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                    else:
                        self.logit('init_okx', '[ERROR] What is this ... [quit]') # noqa
                        self.page.quit()

        self.logit('init_okx', 'login failed [ERROR]')
        return False

    def save_screenshot(self, name):
        # 对整页截图并保存
        # self.page.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        self.page.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def update_status(self, update_ts=None):
        if not update_ts:
            update_ts = time.time()
            update_ts += 86400

        # 随机增加一点时间
        add_ts = random.randint(180, 300)
        update_ts += add_ts
        update_time = format_ts(update_ts, 2, TZ_OFFSET)
        if self.args.s_profile in self.dic_status:
            self.dic_status[self.args.s_profile][1] = update_time
        else:
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
                update_time
            ]
        self.status_save()
        self.is_update = True

    def get_faucet_time(slef, s_info):
        """
        # noqa
        # Test the function with the provided examples
        test1 = "Faucet resets in 24 hours have passed"
        test2 = "You have exceeded the rate limit. Please wait 16 hours 9 minutes 45 seconds before you try again."

        get_faucet_time(test1), get_faucet_time(test2)
        """
        # Check if the string contains "Faucet resets in 24 hours have passed"
        if "Faucet resets in 24 hours have passed" in s_info:
            return datetime.now().timestamp()

        # Extract time information from the string
        elif "Please wait" in s_info:
            # Find the index where the time information starts
            time_start_index = s_info.find("Please wait") + len("Please wait") # noqa
            # Extract the time string
            time_str = s_info[time_start_index:].strip()

            # Parse the time string to get days, hours, minutes, and seconds
            days = 0
            hours = 0
            minutes = 0
            seconds = 0
            # if 'd' in time_str:
            #     days = int(time_str.split('days')[0])
            #     time_str = time_str.split('days')[1].strip()
            if 'h' in time_str:
                hours = int(time_str.split('hours')[0])
                time_str = time_str.split('hours')[1].strip()
            if 'm' in time_str:
                minutes = int(time_str.split('minutes')[0])
                time_str = time_str.split('minutes')[1].strip()
            if 's' in time_str:
                seconds = int(time_str.split('seconds')[0])

            new_time = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds) # noqa
            return new_time.timestamp()

        else:
            return None

    def okx_connect(self):
        # OKX Wallet Connect
        self.save_screenshot(name='page_wallet_connect.jpg')
        if len(self.page.tab_ids) == 2:
            tab_id = self.page.latest_tab
            tab_new = self.page.get_tab(tab_id)
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit(None, 'OKX Wallet Connect')
                self.page.wait(1)
                return True
        return False

    def okx_approve(self):
        # OKX Wallet Add network
        if len(self.page.tab_ids) == 2:
            tab_id = self.page.latest_tab
            tab_new = self.page.get_tab(tab_id)
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit(None, 'OKX Wallet Add network')
                self.page.wait(1)
                return True
        return False

    def get_tag_info(self, s_tag, s_text):
        """
        s_tag:
            span
            div
        """
        s_path = f'@@tag()={s_tag}@@text():{s_text}'
        ele_info = self.page.ele(s_path, timeout=1)
        if not isinstance(ele_info, NoneElement):
            # self.logit(None, f'[html] {s_text}: {ele_info.html}')
            s_info = ele_info.text.replace('\n', ' ')
            self.logit(None, f'[info][{s_tag}] {s_text}: {s_info}')
            return True
        return False

    def get_index_from_header(self, header, field):
        """
        根据给定的字段获取其在header中的下标。

        参数:
            header (str): 以逗号分隔的字段字符串，例如 "account,purse,evm_address,vpn"
            field (str): 需要查找的字段名称，例如 "vpn"

        返回:
            int: 字段在header中的下标，如果字段不存在则返回 -1
        """
        # 将header字符串分割为列表
        fields = header.split(',')
        # 获取字段的下标
        try:
            index = fields.index(field)
        except ValueError:
            # 如果字段不存在，返回 -1
            index = -1
        return index

    def set_vpn(self):
        idx_vpn = self.get_index_from_header(DEF_HEADER_PURSE, 'vpn')
        try:
            s_vpn = self.dic_purse[self.args.s_profile][idx_vpn]
        except: # noqa
            s_vpn = 'NULL'
        self.logit(None, f'Set VPN to {s_vpn} ...')
        d_cont = {
            'title': f'Set VPN to {s_vpn} ! [sahara_faucet]',
            'text': (
                'Faucet Set VPN [sahara_faucet]\n'
                f'- profile: {self.args.s_profile}\n'
                f'- vpn: {s_vpn}\n'
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")
        pdb.set_trace()

    def faucet_claim(self):
        """
        """
        self.set_vpn()

        for i in range(1, DEF_NUM_TRY):
            self.logit('faucet_claim', f'Faucet Summit try_i={i}/{DEF_NUM_TRY}') # noqa

            if self.init_okx() is False:
                self.page.wait(2)
                continue

            self.page.get(DEF_URL_FAUCET)
            # self.page.wait.load_start()
            self.page.wait(3)

            self.logit('faucet_claim', f'tabs_count={self.page.tabs_count}')

            # ele_btn = self.page.ele('@@tag()=button@@text()=Connect Wallet', timeout=2) # noqa
            # if not isinstance(ele_btn, NoneElement):
            #     ele_btn.click(by_js=True)
            #     self.page.wait(1)

            # 钱包未连接
            ele_btn = self.page.ele('@@tag()=div@@class:iekbcc0 ', timeout=2) # noqa
            # Connect Wallet
            # Wrong network\nDropdown
            if not isinstance(ele_btn, NoneElement):
                s_info = ele_btn.text.replace('\n', ' ')
                self.logit(None, f'Wallet Connect Status: {s_info}')
                if s_info.find('Connect Wallet') >= 0:
                    ele_btn.click()
                    self.page.wait(2)
                    ele_wallet_btn = self.page.ele('@@tag()=div@@class=iekbcc0 ju367v5p@@text()=OKX Wallet', timeout=2) # noqa
                    if not isinstance(ele_wallet_btn, NoneElement):
                        ele_wallet_btn.click(by_js=True)
                elif s_info.find('Wrong network') >= 0:
                    ele_btn.click()
                    self.page.wait(2)
                    ele_btn = self.page.ele('@@tag()=div@@text()=SaharaAI Testnet', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.logit(None, 'Switch Networks ...')
                self.page.wait(1)

                # OKX Wallet Connect
                self.okx_connect()
                # OKX Wallet Add network
                self.okx_approve()

            # get balance
            ele_info = self.page.ele('@@tag()=div@@class:iekbcc0@@text():SAHARA', timeout=2) # noqa
            if not isinstance(ele_info, NoneElement):
                s_info = ele_info.text
                s_info = s_info.split('\n')[0]
                self.logit(None, f'SAHARA balance: {s_info}')
            else:
                self.logit(None, 'Fail to get SAHARA balance')
                self.page.wait(2)
                continue

            # Verify you are human
            max_wait_sec = 30
            for i in range(max_wait_sec+1):
                if self.get_tag_info('span', 'Ready!'):
                    break
                self.logit(None, f'{i}/{max_wait_sec} Verify you are human ...') # noqa
                self.page.wait(1)
                self.get_tag_info('span', 'In process')
                # auto_click()
            if i >= max_wait_sec:
                self.logit(None, f'{i}/{max_wait_sec} Verify Failed') # noqa
                self.page.wait(3)
                continue

            # Claim Button
            for j in range(1, 10):
                button = self.page.ele('@@tag()=button@@text()=Request', timeout=2) # noqa
                if button.states.is_enabled:
                    break
                self.logit(None, 'Wait Request button ...')
                time.sleep(j)

            if button.states.is_enabled:
                # self.page.wait.load_start()

                i = 0
                max_wait_sec = 6
                while i < max_wait_sec:
                    i += 1
                    if button.click(by_js=True):
                        self.logit(None, 'Wait Request button ...')
                        self.page.wait(1)
                    if self.get_tag_info('span', 'complete the captcha'):
                        self.page.wait(10)
                        continue

                    # Request sent successfully. Please wait a moment.
                    if self.get_tag_info('span', 'successfully'):
                        self.update_status()
                        self.is_update = True
                        self.logit(None, 'Faucet Claim Success!')

                    # You have exceeded the rate limit. Please wait 23 hours 59 minutes 43 seconds before you try again. # noqa
                    s_path = '@@tag()=span@@text():exceeded'
                    ele_info = self.page.ele(s_path, timeout=1)
                    if not isinstance(ele_info, NoneElement):
                        # print(ele_info.html)
                        s_info = ele_info.text.replace('\n', ' ')
                        self.logit(None, f'Faucet info: {s_info}')
                        if s_info.find('loading') >= 0:
                            self.page.wait(1)
                            continue
                        avail_ts = self.get_faucet_time(ele_info.text)
                        avail_time = format_ts(avail_ts, 2, TZ_OFFSET)
                        self.logit(None, f'To claim at {avail_time}')

                        s_avail_time_pre = self.get_status_by_idx(IDX_UPDATE)
                        if not s_avail_time_pre:
                            self.update_status(avail_ts)
                            self.is_update = True
                            self.logit(None, 'Update status file.')
                        self.logit(None, 'Faucet already claimed!')
                        return True
                    else:
                        s_path = '@@tag()=div@@class:flex items-center justify-center@@text():position in the queue' # noqa
                        ele_info = self.page.ele(s_path, timeout=1)
                        if not isinstance(ele_info, NoneElement):
                            s_info = ele_info.text.replace('\n', ' ')
                            self.logit(None, f'[queue] {s_info}')
                        else:
                            # Captcha verification failed:Captcha verification failed:["invalid-input-response"], please try again # noqa
                            s_path = '@@tag()=div@@class=sa-v4-message-custom-content sa-v4-message-warning' # noqa
                            ele_info = self.page.ele(s_path, timeout=1)
                            if not isinstance(ele_info, NoneElement):
                                s_info = ele_info.text.replace('\n', ' ')
                                self.logit(None, f'[message-warning] {s_info}')
                                self.page.wait(3)
                            else:
                                self.get_tag_info('div', 'failed')

                    self.logit(None, f'Wait:{i} seconds ...')
                    self.page.wait(1)
                if i >= max_wait_sec:
                    self.logit(None, f'Fail to get claim info, took {i} seconds.') # noqa
                    continue

                else:
                    self.logit(None, 'Failed to click request button.')
            else:
                self.page.refresh()
                self.page.wait.load_start()
                pass

        self.logit('faucet_claim', 'Claim finished!')
        self.close()
        return False


def send_msg(instFaucetTask, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            if s_profile in instFaucetTask.dic_status:
                lst_status = instFaucetTask.dic_status[s_profile]
            else:
                lst_status = [s_profile, -1]

            s_info += '- {} {}\n'.format(
                s_profile,
                lst_status[1],
            )
        d_cont = {
            'title': 'Daily Active Finished! [sahara_faucet]',
            'text': (
                'Faucet claim [sahara_faucet]\n'
                '- {}\n'
                '{}\n'
                .format(DEF_HEADER_STATUS, s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    instFaucetTask = FaucetTask()

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(instFaucetTask.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    lst_wait = []
    # 将已完成的剔除掉
    instFaucetTask.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in instFaucetTask.dic_status:
            lst_status = instFaucetTask.dic_status[s_profile]
            if lst_status:
                avail_time = lst_status[1]
                if avail_time:

                    n_sec_wait = time_difference(avail_time) + 1
                    if n_sec_wait > 0:
                        lst_wait.append([s_profile, n_sec_wait])
                        # logger.info(f'[{s_profile}] 还需等待{n_sec_wait}秒') # noqa
                        n += 1
                        profiles.pop(i)
        else:
            continue
    logger.info('#'*40)
    if len(lst_wait) > 0:
        n_top = 5
        logger.info(f'***** Top {n_top} wait list')
        sorted_lst_wait = sorted(lst_wait, key=lambda x: x[1], reverse=False)
        for (s_profile, n_sec_wait) in sorted_lst_wait[:n_top]:
            logger.info(f'[{s_profile}] 还需等待{seconds_to_hms(n_sec_wait)}') # noqa
    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in instFaucetTask.dic_purse:
            logger.info(f'{s_profile} is not in purse conf [ERROR]')
            sys.exit(0)

        def _run():
            s_directory = f'{DEF_PATH_USER_DATA}/{args.s_profile}'
            if os.path.exists(s_directory) and os.path.isdir(s_directory):
                pass
            else:
                # Create new profile
                instFaucetTask.initChrome(args.s_profile)
                instFaucetTask.init_okx()
                instFaucetTask.close()
            instFaucetTask.initChrome(args.s_profile)
            is_claim = instFaucetTask.faucet_claim()
            return is_claim

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                is_claim = False
                if j > 1:
                    logger.info(f'异常重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                instFaucetTask.set_args(args)
                instFaucetTask.status_load()

                if s_profile in instFaucetTask.dic_status:
                    lst_status = instFaucetTask.dic_status[s_profile]
                else:
                    lst_status = None

                is_claim = False
                is_ready_claim = True
                if lst_status:
                    avail_time = lst_status[1]

                    if avail_time:
                        n_sec_wait = time_difference(avail_time) + 1
                        if n_sec_wait > 0:
                            logger.info(f'[{s_profile}] 还需等待{n_sec_wait}秒') # noqa
                            is_ready_claim = False
                            break

                if is_ready_claim:
                    is_claim = _run()

                if is_claim:
                    lst_success.append(s_profile)
                    instFaucetTask.close()
                    break

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                instFaucetTask.close()
                if j < max_try_except:
                    time.sleep(5)

        if instFaucetTask.is_update is False:
            continue

        logger.info(f'[{s_profile}] Finish')

        if len(items) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    send_msg(instFaucetTask, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    if args.loop_interval <= 0:
        main(args)
    else:
        while True:
            main(args)
            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
python3 sahara_faucet.py --sleep_sec_min=30 --sleep_sec_max=60 --loop_interval=60
python3 sahara_faucet.py --sleep_sec_min=600 --sleep_sec_max=1800 --loop_interval=60
"""
