"""
豆子设计助手 - 后端服务入口
"""
from flask import Flask, jsonify
from config import Config
from routes.activation import activation_bp
from routes.payment import payment_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 注册蓝图
    app.register_blueprint(activation_bp, url_prefix='/api/activation')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    
    # 健康检查接口
    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'service': 'bean-design-assistant-server'})
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
