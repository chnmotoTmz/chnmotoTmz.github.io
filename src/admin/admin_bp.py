from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.database import db, BlogConfig

admin_bp = Blueprint('admin', __name__, template_folder='../../templates', url_prefix='/admin')

@admin_bp.route('/blogconfig')
def blogconfig_list():
    configs = db.session.query(BlogConfig).order_by(BlogConfig.blog_id, BlogConfig.key).all()
    return render_template('blogconfig_list.html', configs=configs)

@admin_bp.route('/blogconfig/edit/<int:config_id>', methods=['GET', 'POST'])
def blogconfig_edit(config_id):
    config = db.session.query(BlogConfig).get(config_id)
    if request.method == 'POST':
        config.value = request.form['value']
        db.session.commit()
        flash('更新しました', 'success')
        return redirect(url_for('admin.blogconfig_list'))
    return render_template('blogconfig_edit.html', config=config)

@admin_bp.route('/blogconfig/add', methods=['GET', 'POST'])
def blogconfig_add():
    if request.method == 'POST':
        blog_id = request.form['blog_id']
        key = request.form['key']
        value = request.form['value']
        config = BlogConfig(blog_id=blog_id, key=key, value=value)
        db.session.add(config)
        db.session.commit()
        flash('追加しました', 'success')
        return redirect(url_for('admin.blogconfig_list'))
    return render_template('blogconfig_add.html')

@admin_bp.route('/blogconfig/delete/<int:config_id>', methods=['POST'])
def blogconfig_delete(config_id):
    config = db.session.query(BlogConfig).get(config_id)
    db.session.delete(config)
    db.session.commit()
    flash('削除しました', 'success')
    return redirect(url_for('admin.blogconfig_list'))
