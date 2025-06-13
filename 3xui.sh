#!/bin/bash

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[36m"
PLAIN='\033[0m'

XUI_DB="/usr/local/x-ui/x-ui.db"
getPublicIP() {
    IP=$(curl -sL -4 ip.sb 2>/dev/null)
    [[ -z "$IP" ]] && IP=$(curl -sL -6 ip.sb 2>/dev/null)
}

# 生成随机uuid
genUUID() { cat /proc/sys/kernel/random/uuid; }
# 生成随机path
genPath() { echo "/$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c8)"; }
# 随机端口
genPort() { shuf -i16000-40000 -n1; }

ensure_tools() {
    for tool in sqlite3 qrencode jq; do
        command -v $tool >/dev/null 2>&1 || apt install -y $tool || yum install -y $tool
    done
}
ensure_tools

# 写入sqlite函数
add_xui_inbound() {
    proto="$1"
    port="$2"
    uuid="$3"
    path="$4"
    domain="$5"
    remark="$6"
    network="$7"
    ws_host="$8"
    security="$9"
    flow="${10}" # for xtls
    # 填充完整插入语句（以下仅为vless/ws/tls举例，其他协议可仿写，按3x-ui源码db结构）

    # enabled=1, sniffing, timeout, etc 可参考已存在记录
    INSERT="INSERT INTO inbounds (listen_ip,listen_port,protocol,uuid,remark,enable,sniffing,network,ws_host,ws_path,flow,tls,host,path,created_at,updated_at) VALUES ('0.0.0.0',$port,'$proto','$uuid','$remark',1,1,'$network','$ws_host','$path','$flow',1,'$domain','$path',strftime('%s','now'),strftime('%s','now'));"
    sqlite3 "$XUI_DB" "$INSERT"
}

# Bash生成配置并添加到x-ui.db
gen_vless_ws_tls() {
    getPublicIP
    echo -e "${YELLOW}===== 一键生成VLESS+WS+TLS节点 =====${PLAIN}"
    read -p "请输入伪装域名（可cdn加速）: " DOMAIN
    [[ -z "$DOMAIN" ]] && { echo -e "${RED}域名不可为空${PLAIN}"; return; }
    read -p "请输入监听端口[回车随机]:" PORT; [[ -z "$PORT" ]] && PORT=$(genPort)
    UUID=$(genUUID)
    PATH=$(genPath)
    REMARK="VLESS-WS-TLS"
    NETWORK="ws"
    echo -e "节点信息："
    echo -e "  域名: $DOMAIN"
    echo -e "  端口: $PORT"
    echo -e "  uuid: $UUID"
    echo -e "  path: $PATH"
    echo -e "开始写入3x-ui数据库..."
    add_xui_inbound "vless" "$PORT" "$UUID" "$PATH" "$DOMAIN" "$REMARK" "$NETWORK" "$DOMAIN" "tls"
    systemctl restart x-ui
    sleep 2
    # 输出链接
    link="vless://${UUID}@${DOMAIN}:${PORT}?encryption=none&type=ws&security=tls&host=${DOMAIN}&path=${PATH}#${REMARK}"
    echo -e "节点链接：${GREEN}$link${PLAIN}"
    qrencode -o - -t utf8 "$link"
}

# 补全菜单调用与控制
main_menu() {
    clear
    echo -e "${BLUE}3x-ui命令行一键节点生成器${PLAIN}\n"
    echo "  1. 一键生成VLESS+WS+TLS节点"
    echo "  2. 一键生成VMESS+WS+TLS节点"
    echo "  3. 一键生成Trojan+TLS节点"
    echo "  4. 一键生成VLESS+XTLS节点"
    echo "  5. 一键生成SOCKS5节点"
    echo "-----------------"
    echo "  0.  退出"
    read -p "请选择：" sel
    case $sel in
        1) gen_vless_ws_tls ;;
        2) gen_vmess_ws_tls ;;
        3) gen_trojan_tls ;;
        4) gen_vless_xtls ;;
        5) gen_socks5 ;;
        0) exit 0 ;;
        *) echo -e "${RED}输入有误${PLAIN}";;
    esac
    echo; read -p "回车返回菜单..." temp
    main_menu
}

# 这里再补充其他各种协议生成功能函数（如下举例）
gen_vmess_ws_tls() {
    getPublicIP
    echo -e "${YELLOW}===== 一键生成VMESS+WS+TLS节点 =====${PLAIN}"
    read -p "请输入伪装域名: " DOMAIN
    [[ -z "$DOMAIN" ]] && { echo -e "${RED}域名不可为空${PLAIN}"; return; }
    read -p "请输入监听端口[回车随机]:" PORT; [[ -z "$PORT" ]] && PORT=$(genPort)
    UUID=$(genUUID)
    PATH=$(genPath)
    REMARK="VMESS-WS-TLS"
    NETWORK="ws"
    echo -e "开始写入3x-ui数据库..."
    add_xui_inbound "vmess" "$PORT" "$UUID" "$PATH" "$DOMAIN" "$REMARK" "$NETWORK" "$DOMAIN" "tls"
    systemctl restart x-ui
    sleep 2
    # VMESS节点link
    raw="{\"v\":\"2\",\"ps\":\"$REMARK\",\"add\":\"$DOMAIN\",\"port\":\"$PORT\",\"id\":\"$UUID\",\"aid\":\"0\",\"net\":\"ws\",\"type\":\"none\",\"host\":\"$DOMAIN\",\"path\":\"$PATH\",\"tls\":\"tls\"}"
    link="vmess://$(echo -n $raw | base64 -w0)"
    echo -e "节点链接：${GREEN}$link${PLAIN}"
    qrencode -o - -t utf8 "$link"
}

gen_trojan_tls() {
    getPublicIP
    echo -e "${YELLOW}===== 一键生成Trojan+TLS节点 =====${PLAIN}"
    read -p "请输入伪装域名: " DOMAIN
    [[ -z "$DOMAIN" ]] && { echo -e "${RED}域名不可为空${PLAIN}"; return; }
    read -p "请输入监听端口[回车随机]:" PORT; [[ -z "$PORT" ]] && PORT=$(genPort)
    PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c16)
    REMARK="TROJAN-TLS"
    NETWORK="tcp"
    add_xui_inbound "trojan" "$PORT" "$PASSWORD" "" "$DOMAIN" "$REMARK" "$NETWORK" "$DOMAIN" "tls"
    systemctl restart x-ui
    sleep 2
    link="trojan://${PASSWORD}@${DOMAIN}:${PORT}#${REMARK}"
    echo -e "节点链接：${GREEN}$link${PLAIN}"
    qrencode -o - -t utf8 "$link"
}

gen_vless_xtls() {
    getPublicIP
    read -p "请输入域名: " DOMAIN; [[ -z "$DOMAIN" ]] && { echo -e "${RED}域名不可为空${PLAIN}"; return; }
    read -p "请输入端口[443]:" PORT; [[ -z $PORT ]] && PORT=443
    UUID=$(genUUID)
    REMARK="VLESS-XTLS"
    FLOW="xtls-rprx-direct"
    add_xui_inbound "vless" "$PORT" "$UUID" "" "$DOMAIN" "$REMARK" "tcp" "$DOMAIN" "xtls" "$FLOW"
    systemctl restart x-ui
    sleep 2
    link="vless://${UUID}@${DOMAIN}:${PORT}?encryption=none&security=xtls&type=tcp&flow=${FLOW}#${REMARK}"
    echo -e "节点链接：${GREEN}$link${PLAIN}"
    qrencode -o - -t utf8 "$link"
}

gen_socks5() {
    read -p "请输入监听端口[回车随机]:" PORT; [[ -z "$PORT" ]] && PORT=$(genPort)
    PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c16)
    UUID=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c8)
    REMARK="SOCKS5"
    add_xui_inbound "socks" "$PORT" "$UUID" "" "" "$REMARK" "tcp"
    systemctl restart x-ui
    sleep 2
    ip=$(getPublicIP)
    link="socks5://${UUID}:${PASSWORD}@${ip}:${PORT}#${REMARK}"
    echo -e "节点链接：${GREEN}$link${PLAIN}"
    qrencode -o - -t utf8 "$link"
}

# 主入口
main_menu
