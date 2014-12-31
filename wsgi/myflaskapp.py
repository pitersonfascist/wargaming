# -*- coding: utf-8 -*-
from warg import app

import warg.views
import warg.views.users
import warg.views.user_memos
import warg.views.tanks
import warg.views.battle
import warg.views.battle_followers
import warg.views.groups
import warg.views.clan
import warg.views.followers
#import warg.views.categories
import warg.views.system
import warg.views.full_text
import warg.views.chat


if __name__ == "__main__":
    app.run()