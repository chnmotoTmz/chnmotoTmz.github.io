from flask import Blueprint, render_template, request, redirect, url_for, flash
import os
from dotenv import dotenv_values

envvars_bp = Blueprint('envvars', __name__, template_folder='../../templates', url_prefix='/admin')

@envvars_bp.route('/envvars')
def envvars_list():
    # .env, .env.production の両方を読み込む
    env_files = ['.env']
    env_data = {}
    for env_file in env_files:
        if os.path.exists(env_file):
            env_data[env_file] = dotenv_values(env_file)
        else:
            env_data[env_file] = None
    return render_template('envvars_list.html', env_data=env_data)
