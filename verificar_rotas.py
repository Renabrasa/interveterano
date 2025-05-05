from main import app

with app.app_context():
    print("\n📋 ROTAS REGISTRADAS NO FLASK:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.methods} => {rule.rule}")
