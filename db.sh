#!/bin/bash
# 数据库信息查询脚本
# 用于显示data目录下所有SQLite数据库的表结构信息

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # 无颜色

# 检查data目录是否存在
if [ ! -d "data" ]; then
    echo -e "${RED}Error: data目录不存在${NC}"
    echo "请在项目根目录下运行此脚本"
    exit 1
fi

# 检查是否安装了sqlite3
if ! command -v sqlite3 &> /dev/null; then
    echo -e "${YELLOW}未找到sqlite3命令，尝试自动安装...${NC}"
    
    # 检测Alpine环境并安装
    if [ -f /etc/alpine-release ]; then
        echo -e "${CYAN}检测到Alpine环境，使用apk安装sqlite...${NC}"
        apk add --no-cache sqlite
    else
    echo -e "${RED}Error: 未找到sqlite3命令${NC}"
    echo "请安装sqlite3: "
    echo "  - Ubuntu/Debian: sudo apt-get install sqlite3"
    echo "  - MacOS: brew install sqlite3"
    echo "  - Windows: 请下载SQLite并添加到PATH"
    exit 1
    fi
    
    # 再次检查安装是否成功
    if ! command -v sqlite3 &> /dev/null; then
        echo -e "${RED}自动安装sqlite3失败，请手动安装${NC}"
        exit 1
    else
        echo -e "${GREEN}sqlite3安装成功，继续执行...${NC}"
    fi
fi

# 声明全局数组变量用于存储数据库文件
declare -a DB_FILES

# 获取data目录下所有数据库文件
get_all_db_files() {
    # 清空数组
    DB_FILES=()
    
    # 查找data目录下所有.db文件
    for file in data/*.db; do
        # 检查文件是否存在且是常规文件
        if [ -f "$file" ]; then
            DB_FILES+=("$file")
        fi
    done
    
    # 如果未找到任何数据库文件，使用默认列表
    if [ ${#DB_FILES[@]} -eq 0 ]; then
        echo -e "${YELLOW}未在data目录下找到任何.db文件，使用默认列表${NC}"
DB_FILES=("data/sign.db" "data/log.db" "data/set.db")
    else
        echo -e "${GREEN}发现 ${#DB_FILES[@]} 个数据库文件${NC}"
    fi
    
    # 打印找到的所有数据库文件
    echo -e "${CYAN}数据库文件列表:${NC}"
    for db in "${DB_FILES[@]}"; do
        echo "  - $db"
    done
    
    echo ""
}

# 获取数据库文件列表
get_all_db_files

# 统计变量
TOTAL_TABLES=0
TOTAL_RECORDS=0

echo -e "${GREEN}======================================${NC}"
echo -e "${CYAN}数据库信息查询工具 v1.0${NC}"
echo -e "${GREEN}======================================${NC}"

# 遍历每个数据库文件
for DB_FILE in "${DB_FILES[@]}"; do
    # 检查数据库文件是否存在
    if [ ! -f "$DB_FILE" ]; then
        echo -e "${YELLOW}警告: 数据库文件 $DB_FILE 不存在, 跳过${NC}"
        continue
    fi
    
    echo -e "\n${BLUE}数据库: $DB_FILE${NC}"
    echo -e "${GREEN}--------------------------------------${NC}"
    
    # 获取所有表名
    TABLES=$(sqlite3 "$DB_FILE" ".tables")
    
    # 如果没有表，显示警告并继续
    if [ -z "$TABLES" ]; then
        echo -e "${YELLOW}此数据库没有表${NC}"
        continue
    fi
    
    # 将表名字符串分割成数组
    IFS=' ' read -ra TABLE_ARRAY <<< "$TABLES"
    DB_TABLE_COUNT=0
    DB_RECORD_COUNT=0
    
    # 处理每个表
    for TABLE in "${TABLE_ARRAY[@]}"; do
        # 获取表的行数
        ROW_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM $TABLE;")
        
        echo -e "${PURPLE}表名: $TABLE${NC} (${YELLOW}${ROW_COUNT}条记录${NC})"
        
        # 获取表结构
        echo -e "${CYAN}表结构:${NC}"
        sqlite3 "$DB_FILE" ".schema $TABLE" | sed 's/^/  /'
        
        # 如果表有记录，显示一行示例数据
        if [ "$ROW_COUNT" -gt 0 ]; then
            echo -e "${CYAN}示例数据:${NC}"
            
            # 构建获取所有列名的查询
            COLUMNS=$(sqlite3 "$DB_FILE" "PRAGMA table_info($TABLE);" | awk -F'|' '{print $2}' | tr '\n' ',' | sed 's/,$//')
            
            # 构建查询语句，限制结果为1行
            SELECT_QUERY="SELECT * FROM $TABLE LIMIT 1;"
            
            # 执行查询并美化输出
            echo -e "  $(sqlite3 -header -column "$DB_FILE" "$SELECT_QUERY" | head -n 1)"
            echo -e "  $(sqlite3 -header -column "$DB_FILE" "$SELECT_QUERY" | tail -n 1)"
        else
            echo -e "${YELLOW}  表为空，无示例数据${NC}"
        fi
        
        echo ""
        
        # 更新统计
        DB_TABLE_COUNT=$((DB_TABLE_COUNT + 1))
        DB_RECORD_COUNT=$((DB_RECORD_COUNT + ROW_COUNT))
    done
    
    # 显示该数据库的统计信息
    echo -e "${GREEN}$DB_FILE 统计信息:${NC}"
    echo -e "  ${YELLOW}表数量: $DB_TABLE_COUNT${NC}"
    echo -e "  ${YELLOW}总记录数: $DB_RECORD_COUNT${NC}"
    
    # 更新总统计
    TOTAL_TABLES=$((TOTAL_TABLES + DB_TABLE_COUNT))
    TOTAL_RECORDS=$((TOTAL_RECORDS + DB_RECORD_COUNT))
done

# 显示总统计
echo -e "\n${GREEN}======================================${NC}"
echo -e "${BLUE}总体统计:${NC}"
echo -e "  ${YELLOW}总表数: $TOTAL_TABLES${NC}"
echo -e "  ${YELLOW}总记录数: $TOTAL_RECORDS${NC}"
echo -e "${GREEN}======================================${NC}"

# 如果没有找到有效的数据库文件，显示提醒
if [ $TOTAL_TABLES -eq 0 ]; then
    echo -e "\n${YELLOW}提示: 未找到任何表，可能的原因:${NC}"
    echo "  1. 应用程序尚未初始化"
    echo "  2. 数据目录路径不正确"
    echo "  3. 数据库结构已更改"
    echo -e "\n建议运行以下命令初始化数据库:"
    echo -e "  ${CYAN}python -c \"from app.utils.db_init import initialize_database; initialize_database()\"${NC}"
fi

exit 0 