from sqlalchemy import inspect, text

with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    if "couriers" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("couriers")}
        alter_statements = []
        if "full_name" not in existing_cols:
            alter_statements.append("ALTER TABLE couriers ADD COLUMN full_name VARCHAR(140)")
        if "cpf" not in existing_cols:
            alter_statements.append("ALTER TABLE couriers ADD COLUMN cpf VARCHAR(20)")
        if "lat" not in existing_cols:
            alter_statements.append("ALTER TABLE couriers ADD COLUMN lat DOUBLE PRECISION")
        if "lng" not in existing_cols:
            alter_statements.append("ALTER TABLE couriers ADD COLUMN lng DOUBLE PRECISION")
        if "created_at" not in existing_cols:
            alter_statements.append("ALTER TABLE couriers ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE")

        if alter_statements:
            with db.engine.begin() as conn:
                for stmt in alter_statements:
                    conn.execute(text(stmt))
                if "name" in existing_cols and "full_name" not in existing_cols:
                    conn.execute(text("UPDATE couriers SET full_name = name WHERE full_name IS NULL"))
