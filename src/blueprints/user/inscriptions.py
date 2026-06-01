


import logging
from flask import abort, g, redirect, render_template, request, send_file, session, url_for, jsonify, Blueprint
from . import inscriptions_bp
from src.blueprints.contents.routes import get_banner
logger = logging.getLogger(__name__)



@inscriptions_bp.route('/subscribe/<content_id>', methods=['POST'])
def subscribe(content_id):
    print("eu pelo menos tento?")
    try:       
        if g.user.new_inscription(content_id):
            print("pelo menos da certo 1")
            return redirect(url_for("contents.content_buss", content_id = content_id))
        print("Deu merda 1")
        return jsonify({'error': 'Conteúdo não encontrado'}), 404            
    except:
        print("Deu merda 2")
        return jsonify({'error': 'Conteúdo não encontrado'}), 404

def unsubscribe(content_id):
    try:
        if g.user.remove_incription(content_id):
            return True
    except:
        return False        
    
@inscriptions_bp.route('/user/unsubscribe/<content_id>', methods=['DELETE', 'POST'])
def unsubscribe_by_my_content_pages(content_id):
    if unsubscribe(content_id):
        return render_template("contents.my_inscriptions.html")
    return redirect(url_for("manager_course", course = content_id))
    
@inscriptions_bp.route('/unsubscribe/<content_id>', methods=['DELETE', 'POST'])
def unsubscribe_preview(content_id):
    
    
    unsubscribe_response = unsubscribe(content_id)
    
    
    if not unsubscribe_response:
        jsonify({'error': 'Não foi possível se desinscrever do conteúdo'}), 404
        
    
    
    if not content:
        jsonify({'error': 'Conteúdo não encontrado'}), 404        
    return redirect(url_for("contents.content_buss", content_id=content_id))

def get_my_courses():
        
    inscriptions = g.user.my_inscriptions()
    courses = []
    try:
        for inscription in inscriptions:
            print("tipo do conteudo e", type(inscription["content_id"]))
            course = g.user.get_content_by_id(inscription["content_id"])
            course["banner"] = get_banner(inscription["content_id"])
            courses.append(course)
            print(course["title"])
                 
        return courses
        
    except:
        return None
            
@inscriptions_bp.route('/my-courses', methods=['GET'])
def my_courses():
    
    try:
        courses = get_my_courses()
        return render_template("my_courses.html", courses = courses)
    
        
    except Exception as e:
        logger.error(f"Erro ao listar inscrições: {e}")
        return jsonify({'error': 'Erro ao recuperar suas inscrições.'}), 500


@inscriptions_bp.route('/is-subscribed/<content_if>', methods=['GET'])
def check_subscription(content_id):
    g.check_inscription(content_id)
    
    
    