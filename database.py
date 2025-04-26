from app import create_app, db
from app.models import PermanentToken, SignLog, Logs, ScheduledTask, TaskLog  # 导入五个模型

def print_table_data(model):
    print(f"\n=== {model.__tablename__} ===")
    records = model.query.all()
    if not records:
        print("表中没有数据")
        return
    
    # 获取模型的所有列名
    columns = [column.key for column in model.__table__.columns]
    
    # 打印表头
    print(" | ".join(columns))
    print("-" * (len(columns) * 15))
    
    # 打印每条记录
    for record in records:
        row_data = []
        for column in columns:
            value = getattr(record, column)
            row_data.append(str(value))
        print(" | ".join(row_data))

def main():
    app = create_app()
    with app.app_context():
        print_table_data(PermanentToken)
        print_table_data(SignLog)
        print_table_data(Logs)
        print_table_data(ScheduledTask)
        print_table_data(TaskLog)
        
if __name__ == "__main__":
    main()
