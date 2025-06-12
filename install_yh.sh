#!/bin/bash
# Xray 一键安装脚本
# Author: 3000mall<wechat:CPLA_54J>
# Optimized for robustness and maintainability

RED="\033[31m"      # 错误信息
GREEN="\033[32m"    # 成功信息
YELLOW="\033[33m"   # 警告信息
BLUE="\033[36m"     # 提示信息
PLAIN='\033[0m'      # 重置样式

# 小说站点列表
SITES=(
    http://www.zhuizishu.com/
    http://xs.56dyc.com/
    http://www.ddxsku.com/
    http://www.biqu6.com/
    https://www.wenshulou.cc/
    http://www.55shuba.com/
    http://www.39shubao.com/
    https://www.23xsw.cc/
    https://www.jueshitangmen.info/
    https://www.zhetian.org/
    http://www.bequgexs.com/
    http://www.tjwl.com/
)

# 全局配置
CONFIG_FILE="/usr/local/etc/xray/config.json"
OS=$(hostnamectl | grep -i system | cut -d: -f2 | tr -d '[:space:]')
NGINX_CONF_PATH="/etc/nginx/conf.d/"
V6_PROXY=""
BT="false"

# 初始化变量
VLESS="false"
TROJAN="false"
TLS="false"
WS="false"
XTLS="false"
KCP="false"

# 颜色输出函数
colorEcho() {
    local color=$1
    shift
    echo -e "${color}$@${PLAIN}"
}

# 获取公网IP
getPublicIP() {
    IP=$(curl -sL -4 ip.sb 2>/dev/null)
    if [[ $? -ne 0 || -z "$IP" ]]; then
        IP=$(curl -sL -6 ip.sb 2>/dev/null)
        V6_PROXY="https://gh.3000mall.com/"
    fi
}

# 检测系统环境
checkSystem() {
    # 检查root权限
    [[ $EUID -ne 0 ]] && { colorEcho $RED "请以root身份执行该脚本"; exit 1; }

    # 检测包管理器
    if command -v yum &>/dev/null; then
        PMT="yum"
        CMD_INSTALL="yum -y install"
        CMD_REMOVE="yum -y remove"
        CMD_UPGRADE="yum -y update"
    elif command -v apt &>/dev/null; then
        PMT="apt"
        CMD_INSTALL="apt -y install"
        CMD_REMOVE="apt -y remove"
        CMD_UPGRADE="apt update && apt -y upgrade && apt -y autoremove"
    else
        colorEcho $RED "不受支持的Linux系统 (仅支持基于 Yum 或 Apt 的系统)"
        exit 1
    fi

    # 检测systemd
    command -v systemctl &>/dev/null || { colorEcho $RED "系统版本过低或未安装 systemd，请升级到最新版本"; exit 1; }

    # 更新软件源
    colorEcho $BLUE "正在更新软件源..."
    if [[ $PMT == "yum" ]]; then
        yum makecache fast -y || { colorEcho $RED "软件源更新失败"; exit 1; }
    else
        apt update -y || { colorEcho $RED "软件源更新失败"; exit 1; }
    fi

    # 检查并安装必要工具
    installRequiredTools() {
        local tools=("$@")
        for tool in "${tools[@]}"; do
            command -v "$tool" &>/dev/null && continue
            
            colorEcho $YELLOW "$tool 未安装，正在安装..."
            if ! $CMD_INSTALL "$tool"; then
                colorEcho $YELLOW "标准安装失败，尝试备选方案..."
                
                if [[ $PMT == "apt" && $(grep -qi "ubuntu" /etc/os-release) ]]; then
                    [[ "$tool" == "qrencode" ]] && tool="libqrencode-dev"
                fi
                
                $CMD_INSTALL "$tool" || {
                    colorEcho $RED "$tool 安装失败，请手动执行以下命令："
                    colorEcho $GREEN "Ubuntu/Debian: sudo apt install -y $tool"
                    colorEcho $GREEN "CentOS/RHEL:   sudo yum install -y $tool"
                    exit 1
                }
            fi
        done
    }

    installRequiredTools qrencode jq
}

# 检测宝塔面板
detectBT() {
    res=$(which bt 2>/dev/null)
    [[ -n "$res" ]] && {
        BT="true"
        NGINX_CONF_PATH="/www/server/panel/vhost/nginx/"
    }
}

# 服务状态检测
status() {
    [[ ! -f /usr/local/bin/xray ]] && { echo 0; return; }
    [[ ! -f $CONFIG_FILE ]] && { echo 1; return; }
    
    port=$(grep port $CONFIG_FILE | head -n 1 | cut -d: -f2 | tr -d \",' ')
    [[ -z "$port" ]] && { echo 1; return; }
    
    res=$(ss -nutlp | grep ":${port} " | grep -i xray)
    [[ -z "$res" ]] && { echo 2; return; }
    
    if [[ $(configNeedNginx) != "yes" ]]; then
        echo 3
    else
        res=$(ss -nutlp | grep -i nginx)
        [[ -z "$res" ]] && echo 4 || echo 5
    fi
}

# 状态文本显示
statusText() {
    case $(status) in
        2) echo -e "${GREEN}已安装${PLAIN} ${RED}未运行${PLAIN}" ;;
        3) echo -e "${GREEN}已安装${PLAIN} ${GREEN}Xray正在运行${PLAIN}" ;;
        4) echo -e "${GREEN}已安装${PLAIN} ${GREEN}Xray正在运行${PLAIN}, ${RED}Nginx未运行${PLAIN}" ;;
        5) echo -e "${GREEN}已安装${PLAIN} ${GREEN}Xray正在运行, Nginx正在运行${PLAIN}" ;;
        *) echo -e "${RED}未安装${PLAIN}" ;;
    esac
}

# 检测是否需要Nginx
configNeedNginx() {
    grep -q wsSettings $CONFIG_FILE && echo yes || echo no
}

needNginx() {
    [[ "$WS" = "true" ]] && echo yes || echo no
}

# 版本规范化
normalizeVersion() {
    local ver=$1
    case "$ver" in
        v*) echo "$ver" ;;
        http*) echo "v1.4.2" ;;
        *) echo "v$ver" ;;
    esac
}

# 获取Xray版本
getVersion() {
    VER=$(/usr/local/bin/xray version 2>/dev/null | head -n1 | awk '{print $2}')
    RETVAL=$?
    CUR_VER=$(normalizeVersion "$(echo "$VER" | head -n 1 | cut -d " " -f2)")
    
    TAG_URL="${V6_PROXY}https://api.github.com/repos/XTLS/Xray-core/releases/latest"
    NEW_VER=$(normalizeVersion "$(curl -s "$TAG_URL" --connect-timeout 10 | grep 'tag_name' | cut -d\" -f4)")
    
    [[ $? -ne 0 || -z "$NEW_VER" ]] && { colorEcho $RED "检查Xray版本信息失败，请检查网络"; return 3; }
    [[ $RETVAL -ne 0 ]] && return 2
    [[ "$NEW_VER" != "$CUR_VER" ]] && return 1
    return 0
}

# 架构检测
archAffix() {
    case "$(uname -m)" in
        x86_64|amd64) echo '64' ;;
        i386|i486|i586|i686) echo '32' ;;
        aarch64|armv8*|arm64) echo 'arm64-v8a' ;;
        armv7l|armv7*) echo 'arm32-v7a' ;;
        armv6l|armv6*) echo 'arm32-v6' ;;
        armv5tel|armv5*) echo 'arm32-v5' ;;
        mips64le) echo 'mips64le' ;;
        mips64) echo 'mips64' ;;
        mipsle) echo 'mips32le' ;;
        mips) echo 'mips32' ;;
        ppc64le) echo 'ppc64le' ;;
        ppc64) echo 'ppc64' ;;
        riscv64) echo 'riscv64' ;;
        s390x) echo 's390x' ;;
        *) colorEcho $RED "不支持的CPU架构: $(uname -m)!"; exit 1 ;;
    esac
}

# 用户输入处理
getData() {
    if [[ "$TLS" = "true" || "$XTLS" = "true" ]]; then
        showTLSRequirements
        handleDomainInput
    fi

    handlePortInput
    handleKCPConfig
    handleTrojanPassword
    handleXTLSFlow
    handleWSPath
    handleProxySite
}

# 显示TLS要求
showTLSRequirements() {
    echo -e "\n${YELLOW}运行之前请确认以下条件已经具备：${PLAIN}"
    colorEcho ${YELLOW} "  1. 一个伪装域名"
    colorEcho ${YELLOW} "  2. 伪装域名DNS解析指向当前服务器ip（${IP}）"
    colorEcho ${BLUE} "  3. 如果/root目录下有 xray.pem 和 xray.key 证书密钥文件，无需理会条件2"
    
    read -p "确认满足按y，按其他退出脚本：" answer
    [[ "${answer,,}" != "y" ]] && exit 0
}

# 处理域名输入
handleDomainInput() {
    local ALLOWED_DOMAINS=("ciuok.com" "dimsn.com" "hhgtk.com")
    
    while true; do
        read -p "请输入伪装域名：" DOMAIN
        DOMAIN=$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]' | sed 's/\.$//')
        
        [[ -z "$DOMAIN" ]] && {
            colorEcho $RED "域名不能为空，请重新输入！"
            continue
        }
        
        local valid=0
        for allowed in "${ALLOWED_DOMAINS[@]}"; do
            if [[ "$DOMAIN" == "$allowed" || "$DOMAIN" =~ \."$allowed"$ ]]; then
                valid=1
                break
            fi
        done
        
        if [[ $valid -eq 0 ]]; then
            colorEcho $RED "当前域名未授权使用，请微信联系3000mall！"
            continue
        fi
        
        checkDomainResolution
        [[ $? -eq 0 ]] && break
    done
    
    colorEcho ${BLUE} "伪装域名(host)：$DOMAIN"
}

# 检查域名解析
checkDomainResolution() {
    if [[ -f ~/xray.pem && -f ~/xray.key ]]; then
        colorEcho ${BLUE} "检测到自有证书，将使用其部署"
        CERT_FILE="/usr/local/etc/xray/${DOMAIN}.pem"
        KEY_FILE="/usr/local/etc/xray/${DOMAIN}.key"
        return 0
    fi

    while true; do
        resolve=$(curl -sL "http://ip-api.com/json/${DOMAIN}")
        if echo "$resolve" | grep -q "\"status\":\"success\""; then
            resolved_ip=$(echo "$resolve" | grep -oP '"query":"\K[^"]+')
            if [[ "$resolved_ip" == "$IP" ]]; then
                return 0
            else
                colorEcho $BLUE "${DOMAIN} 解析结果：${resolved_ip}"
                colorEcho $RED "域名未解析到当前服务器IP(${IP})!"
            fi
        else
            colorEcho $RED "域名解析查询失败"
        fi
        
        colorEcho $YELLOW "请确保域名已正确解析，并尽量稍等1-2分钟（DNS生效），然后重新输入域名。"
        read -p "按回车重新输入域名..." </dev/tty
        return 1
    done
}

# 处理端口输入
handlePortInput() {
    if [[ "$(needNginx)" = "no" ]]; then
        if [[ "$TLS" = "true" ]]; then
            read -p "请输入xray监听端口[强烈建议443，默认443]：" PORT
            [[ -z "$PORT" ]] && PORT=443
        else
            while true; do
                read -p "请输入xray监听端口[100-65535]：" PORT
                [[ -z "$PORT" ]] && PORT=$(shuf -i200-65000 -n1)
                [[ $PORT =~ ^[1-9][0-9]{2,4}$ && $PORT -le 65535 ]] && break
                colorEcho $RED "端口号必须是100-65535之间的数字"
            done
        fi
        colorEcho ${BLUE} "xray端口：$PORT"
    else
        while true; do
            read -p "请输入Nginx监听端口[100-65535，默认443]：" PORT
            [[ -z "$PORT" ]] && PORT=443
            [[ $PORT =~ ^[1-9][0-9]{2,4}$ && $PORT -le 65535 ]] && break
            colorEcho $RED "端口号必须是100-65535之间的数字"
        done
        colorEcho ${BLUE} "Nginx端口：$PORT"
        XPORT=$(shuf -i10000-65000 -n1)
    fi
}

# 处理KCP配置
handleKCPConfig() {
    [[ "$KCP" != "true" ]] && return

    echo -e "\n${BLUE}请选择伪装类型："
    echo "   1) 无"
    echo "   2) BT下载"
    echo "   3) 视频通话"
    echo "   4) 微信视频通话"
    echo "   5) dtls"
    echo "   6) wiregard"
    
    read -p "请选择伪装类型[默认：无]：" answer
    case $answer in
        2) HEADER_TYPE="utp" ;;
        3) HEADER_TYPE="srtp" ;;
        4) HEADER_TYPE="wechat-video" ;;
        5) HEADER_TYPE="dtls" ;;
        6) HEADER_TYPE="wireguard" ;;
        *) HEADER_TYPE="none" ;;
    esac
    
    colorEcho $BLUE "伪装类型：$HEADER_TYPE"
    SEED=$(cat /proc/sys/kernel/random/uuid)
}

# 处理Trojan密码
handleTrojanPassword() {
    [[ "$TROJAN" != "true" ]] && return
    
    read -p "请设置trojan密码（不输则随机生成）:" PASSWORD
    [[ -z "$PASSWORD" ]] && PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)
    colorEcho $BLUE "trojan密码：$PASSWORD"
}

# 处理XTLS流控
handleXTLSFlow() {
    [[ "$XTLS" != "true" ]] && return

    echo -e "\n${BLUE}请选择流控模式:"
    echo -e "   1) xtls-rprx-direct [${RED}推荐${PLAIN}]"
    echo "   2) xtls-rprx-origin"
    
    read -p "请选择流控模式[默认:direct]：" answer
    [[ -z "$answer" ]] && answer=1
    
    case $answer in
        1) FLOW="xtls-rprx-direct" ;;
        2) FLOW="xtls-rprx-origin" ;;
        *) 
            colorEcho $RED "无效选项，使用默认的xtls-rprx-direct"
            FLOW="xtls-rprx-direct" 
            ;;
    esac
    
    colorEcho $BLUE "流控模式：$FLOW"
}

# 处理WS路径
handleWSPath() {
    [[ "$WS" != "true" ]] && return

    while true; do
        read -p "请输入伪装路径，以/开头(不懂请直接回车)：" WSPATH
        if [[ -z "$WSPATH" ]]; then
            len=$(shuf -i5-12 -n1)
            WSPATH="/$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w "$len" | head -n 1)"
            break
        elif [[ "${WSPATH:0:1}" != "/" ]]; then
            colorEcho ${RED} "伪装路径必须以/开头！"
        elif [[ "$WSPATH" = "/" ]]; then
            colorEcho ${RED} "不能使用根路径！"
        else
            break
        fi
    done
    
    colorEcho ${BLUE} "ws路径：$WSPATH"
}

# 处理代理站点
handleProxySite() {
    [[ "$TLS" != "true" && "$XTLS" != "true" ]] && return

    echo -e "\n${BLUE}请选择伪装站类型:"
    echo "   1) 静态网站(位于/usr/share/nginx/html)"
    echo "   2) 小说站(随机选择)"
    echo "   3) 美女站(https://imeizi.me)"
    echo "   4) 高清壁纸站(https://bing.imeizi.me)"
    echo "   5) 自定义反代站点(需以http或者https开头)"
    
    read -p "请选择伪装网站类型[默认:出海导航]：" answer
    if [[ -z "$answer" ]]; then
        PROXY_URL="https://tkstart.com"
    else
        case $answer in
            1) PROXY_URL="" ;;
            2) 
                local len=${#SITES[@]}
                ((len--))
                while true; do
                    index=$(shuf -i0-$len -n1)
                    PROXY_URL=${SITES[$index]}
                    host=$(echo "$PROXY_URL" | cut -d/ -f3)
                    resolve=$(curl -sL "http://ip-api.com/json/$host")
                    [[ "$resolve" =~ "$host" ]] && break
                    echo "$resolve" >> /etc/hosts
                done
                ;;
            3) PROXY_URL="https://imeizi.me" ;;
            4) PROXY_URL="https://bing.imeizi.me" ;;
            5) 
                while true; do
                    read -p "请输入反代站点(以http或者https开头)：" PROXY_URL
                    [[ -n "$PROXY_URL" && "$PROXY_URL" =~ ^https?:// ]] && break
                    colorEcho $RED "反代网站必须以http或https开头！"
                done
                ;;
            *) 
                colorEcho $RED "请输入正确的选项！"
                exit 1
                ;;
        esac
    fi
    
    REMOTE_HOST=$(echo "$PROXY_URL" | cut -d/ -f3)
    colorEcho $BLUE "伪装网站：$PROXY_URL"
    
    echo -e "\n${BLUE}是否允许搜索引擎爬取网站？[默认：不允许]"
    echo "    y)允许，会有更多ip请求网站，但会消耗一些流量，vps流量充足情况下推荐使用"
    echo "    n)不允许，爬虫不会访问网站，访问ip比较单一，但能节省vps流量"
    
    read -p "请选择：[y/n]" answer
    [[ -z "$answer" ]] && ALLOW_SPIDER="n"
    [[ "${answer,,}" = "y" ]] && ALLOW_SPIDER="y" || ALLOW_SPIDER="n"
    colorEcho $BLUE "允许搜索引擎：$ALLOW_SPIDER"
    
    read -p "是否安装BBR(默认安装)?[y/n]:" NEED_BBR
    [[ -z "$NEED_BBR" ]] && NEED_BBR=y
    [[ "$NEED_BBR" = "Y" ]] && NEED_BBR=y
    colorEcho $BLUE "安装BBR：$NEED_BBR"
}

# 安装Nginx
installNginx() {
    [[ "$BT" = "true" ]] && {
        command -v nginx &>/dev/null || {
            colorEcho $RED "您安装了宝塔，请在宝塔后台安装nginx后再运行本脚本"
            exit 1
        }
        return
    }

    colorEcho $BLUE "安装nginx..."
    if [[ "$PMT" = "yum" ]]; then
        if ! yum list installed epel-release &>/dev/null; then
            cat <<EOF > /etc/yum.repos.d/nginx.repo
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/\$releasever/\$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF
        fi
    fi
    
    $CMD_INSTALL nginx || {
        colorEcho $RED "Nginx安装失败，请到微信反馈给3000mall"
        exit 1
    }
    
    systemctl enable nginx
}

# 启动/停止Nginx
startNginx() {
    [[ "$BT" = "true" ]] && nginx -c /www/server/nginx/conf/nginx.conf || systemctl start nginx
}

stopNginx() {
    if [[ "$BT" = "true" ]]; then
        pgrep nginx &>/dev/null && nginx -s stop
    else
        systemctl stop nginx
    fi
}

# 获取证书
getCert() {
    mkdir -p /usr/local/etc/xray
    [[ -n "${CERT_FILE+x}" ]] && return
    
    stopNginx
    systemctl stop xray
    
    # 检查端口占用
    if ss -tuln | grep -q -E ':80\b|:443\b'; then
        colorEcho $RED "其他进程占用了80或443端口，请先关闭再运行一键脚本"
        echo "端口占用信息："
        ss -tuln | grep -E ':80\b|:443\b'
        exit 1
    fi

    # 安装依赖
    $CMD_INSTALL socat openssl
    if [[ "$PMT" = "yum" ]]; then
        $CMD_INSTALL cronie
        systemctl start crond
        systemctl enable crond
    else
        $CMD_INSTALL cron
        systemctl start cron
        systemctl enable cron
    fi

    # 安装acme.sh
    curl -sL https://get.acme.sh | sh -s email=3000mall@dimsn.com
    source ~/.bashrc
    ~/.acme.sh/acme.sh --upgrade --auto-upgrade
    ~/.acme.sh/acme.sh --set-default-ca --server letsencrypt

    # 获取证书
    if [[ "$BT" = "false" ]]; then
        ~/.acme.sh/acme.sh --issue -d $DOMAIN --keylength ec-256 --pre-hook "systemctl stop nginx" --post-hook "systemctl restart nginx" --standalone
    else
        ~/.acme.sh/acme.sh --issue -d $DOMAIN --keylength ec-256 --pre-hook "nginx -s stop" --post-hook "nginx -c /www/server/nginx/conf/nginx.conf" --standalone
    fi

    [[ -f ~/.acme.sh/${DOMAIN}_ecc/ca.cer ]] || {
        colorEcho $RED "获取证书失败，请复制上面的红色文字到微信（3000mall）反馈给我"
        exit 1
    }

    CERT_FILE="/usr/local/etc/xray/${DOMAIN}.pem"
    KEY_FILE="/usr/local/etc/xray/${DOMAIN}.key"
    
    ~/.acme.sh/acme.sh --install-cert -d $DOMAIN --ecc \
        --key-file $KEY_FILE \
        --fullchain-file $CERT_FILE \
        --reloadcmd "service nginx force-reload"
    
    [[ -f $CERT_FILE && -f $KEY_FILE ]] || {
        colorEcho $RED "获取证书失败，请到微信（3000mall）反馈给我"
        exit 1
    }
}

# 配置Nginx
configNginx() {
    mkdir -p /usr/share/nginx/html
    
    # robots.txt配置
    [[ "$ALLOW_SPIDER" = "n" ]] && {
        echo 'User-Agent: *' > /usr/share/nginx/html/robots.txt
        echo 'Disallow: /' >> /usr/share/nginx/html/robots.txt
        ROBOT_CONFIG="    location = /robots.txt {}"
    } || ROBOT_CONFIG=""

    # 非宝塔环境配置
    [[ "$BT" = "false" ]] && {
        [[ ! -f /etc/nginx/nginx.conf.bak ]] && mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
        
        local user="nginx"
        id nginx &>/dev/null || user="www-data"
        
        cat > /etc/nginx/nginx.conf <<'EOF'
user %USER%;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;
    server_tokens off;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;
    gzip                on;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    include /etc/nginx/conf.d/*.conf;
}
EOF
        sed -i "s/%USER%/$user/" /etc/nginx/nginx.conf
    }

    # 生成站点配置
    generateSiteConfig
}

# 生成站点配置
generateSiteConfig() {
    [[ "$TLS" != "true" && "$XTLS" != "true" ]] && return
    
    mkdir -p "${NGINX_CONF_PATH}"
    local action=""
    [[ -n "$PROXY_URL" ]] && action="proxy_ssl_server_name on;
        proxy_pass $PROXY_URL;
        proxy_set_header Accept-Encoding '';
        sub_filter \"$REMOTE_HOST\" \"$DOMAIN\";
        sub_filter_once off;"

    if [[ "$WS" = "true" ]]; then
        # VMESS+WS+TLS 或 VLESS+WS+TLS
        cat > "${NGINX_CONF_PATH}${DOMAIN}.conf" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};
    return 301 https://\$server_name:${PORT}\$request_uri;
}

server {
    listen       ${PORT} ssl http2;
    listen       [::]:${PORT} ssl http2;
    server_name ${DOMAIN};
    charset utf-8;

    # ssl配置
    ssl_protocols TLSv1.1 TLSv1.2;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE:ECDH:AES:HIGH:!NULL:!aNULL:!MD5:!ADH:!RC4;
    ssl_ecdh_curve secp384r1;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    ssl_certificate $CERT_FILE;
    ssl_certificate_key $KEY_FILE;

    root /usr/share/nginx/html;
    location / {
        $action
    }
    $ROBOT_CONFIG

    location ${WSPATH} {
      proxy_redirect off;
      proxy_pass http://127.0.0.1:${XPORT};
      proxy_http_version 1.1;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF
    else
        # VLESS+TCP+TLS 或 VLESS+TCP+XTLS 或 trojan
        cat > "${NGINX_CONF_PATH}${DOMAIN}.conf" <<EOF
server {
    listen 80;
    listen [::]:80;
    listen 81 http2;
    server_name ${DOMAIN};
    root /usr/share/nginx/html;
    location / {
        $action
    }
    $ROBOT_CONFIG
}
EOF
    fi
}

# 设置SELinux
setSelinux() {
    [[ -s /etc/selinux/config ]] && grep 'SELINUX=enforcing' /etc/selinux/config >/dev/null && {
        sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
        setenforce 0
    }
}

# 设置防火墙
setFirewall() {
    # 尝试firewalld
    if command -v firewall-cmd &>/dev/null; then
        systemctl is-active firewalld &>/dev/null && {
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            [[ -n "$PORT" ]] && {
                firewall-cmd --permanent --add-port=${PORT}/tcp
                firewall-cmd --permanent --add-port=${PORT}/udp
            }
            [[ -n "$XPORT" ]] && {
                firewall-cmd --permanent --add-port=${XPORT}/tcp
                firewall-cmd --permanent --add-port=${XPORT}/udp
            }
            firewall-cmd --reload
            return
        }
    fi

    # 尝试ufw
    if command -v ufw &>/dev/null; then
        ufw status | grep -q inactive || {
            ufw allow http/tcp
            ufw allow https/tcp
            [[ -n "$PORT" ]] && {
                ufw allow ${PORT}/tcp
                ufw allow ${PORT}/udp
            }
            [[ -n "$XPORT" ]] && {
                ufw allow ${XPORT}/tcp
                ufw allow ${XPORT}/udp
            }
            return
        }
    fi

    # 使用iptables
    if command -v iptables &>/dev/null; then
        [[ $(iptables -nL | grep -c "Chain FORWARD") -lt 3 ]] && {
            iptables -I INPUT -p tcp --dport 80 -j ACCEPT
            iptables -I INPUT -p tcp --dport 443 -j ACCEPT
            [[ -n "$PORT" ]] && {
                iptables -I INPUT -p tcp --dport ${PORT} -j ACCEPT
                iptables -I INPUT -p udp --dport ${PORT} -j ACCEPT
            }
            [[ -n "$XPORT" ]] && {
                iptables -I INPUT -p tcp --dport ${XPORT} -j ACCEPT
                iptables -I INPUT -p udp --dport ${XPORT} -j ACCEPT
            }
        }
    fi
}

# 安装BBR
installBBR() {
    [[ "$NEED_BBR" != "y" ]] && {
        INSTALL_BBR=false
        return
    }

    # 检查是否已安装BBR
    if lsmod | grep -q bbr; then
        colorEcho $BLUE "官方原版BBR模块已安装"
        INSTALL_BBR=false
        return
    fi

    # 检查OpenVZ
    hostnamectl | grep -i openvz &>/dev/null && {
        colorEcho $BLUE "openvz机器，跳过安装"
        INSTALL_BBR=false
        return
    }

    # 启用BBR
    echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    sysctl -p &>/dev/null

    # 检查是否启用成功
    if lsmod | grep -q bbr; then
        colorEcho $GREEN "官方原版BBR模块已启用"
        INSTALL_BBR=false
        return
    fi

    # 安装新内核
    colorEcho $BLUE "安装官方原版BBR模块..."
    if [[ "$PMT" = "yum" ]]; then
        [[ -z "$V6_PROXY" ]] && {
            rpm --import https://www.elrepo.org/RPM-GPG-KEY-elrepo.org
            rpm -Uvh http://www.elrepo.org/elrepo-release-7.0-4.el7.elrepo.noarch.rpm
            $CMD_INSTALL --enablerepo=elrepo-kernel kernel-ml
            $CMD_REMOVE kernel-3.*
            grub2-set-default 0
            echo "tcp_bbr" >> /etc/modules-load.d/modules.conf
            INSTALL_BBR=true
        }
    else
        $CMD_INSTALL --install-recommends linux-generic-hwe-16.04
        grub-set-default 0
        echo "tcp_bbr" >> /etc/modules-load.d/modules.conf
        INSTALL_BBR=true
    fi
}

# 安装Xray核心
installXrayCore() {
    rm -rf /tmp/xray
    mkdir -p /tmp/xray
    
    # 下载Xray
    local arch=$(archAffix)
    DOWNLOAD_LINK="${V6_PROXY}https://github.com/XTLS/Xray-core/releases/download/${NEW_VER}/Xray-linux-${arch}.zip"
    colorEcho $BLUE "下载Xray: ${DOWNLOAD_LINK}"
    
    if ! curl -L -H "Cache-Control: no-cache" -o /tmp/xray/xray.zip "$DOWNLOAD_LINK"; then
        colorEcho $RED "下载Xray文件失败，请检查服务器网络设置"
        return 1
    fi

    # 解压安装
    unzip /tmp/xray/xray.zip -d /tmp/xray || {
        colorEcho $RED "解压Xray文件失败"
        return 1
    }
    
    systemctl stop xray 2>/dev/null
    mkdir -p /usr/local/etc/xray /usr/local/share/xray
    cp /tmp/xray/xray /usr/local/bin
    cp /tmp/xray/geo* /usr/local/share/xray
    chmod +x /usr/local/bin/xray || {
        colorEcho $RED "Xray安装失败"
        return 1
    }

    return 0
}

# 创建Xray服务
createXrayService() {
    cat > /etc/systemd/system/xray.service <<'EOF'
[Unit]
Description=Xray Service
Documentation=https://github.com/xtls https://3000mall.com
After=network.target nss-lookup.target

[Service]
User=root
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable xray.service
}

# Trojan配置
trojanConfig() {
    cat > $CONFIG_FILE <<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "trojan",
    "settings": {
      "clients": [
        {
          "password": "$PASSWORD"
        }
      ],
      "fallbacks": [
        {
          "alpn": "http/1.1",
          "dest": 80
        },
        {
          "alpn": "h2",
          "dest": 81
        }
      ]
    },
    "streamSettings": {
      "network": "tcp",
      "security": "tls",
      "tlsSettings": {
        "serverName": "$DOMAIN",
        "alpn": ["http/1.1", "h2"],
        "certificates": [
          {
            "certificateFile": "$CERT_FILE",
            "keyFile": "$KEY_FILE"
          }
        ]
      }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

# Trojan+XTLS配置
trojanXTLSConfig() {
    cat > $CONFIG_FILE <<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "trojan",
    "settings": {
      "clients": [
        {
          "password": "$PASSWORD",
          "flow": "$FLOW"
        }
      ],
      "fallbacks": [
        {
          "alpn": "http/1.1",
          "dest": 80
        },
        {
          "alpn": "h2",
          "dest": 81
        }
      ]
    },
    "streamSettings": {
      "network": "tcp",
      "security": "xtls",
      "xtlsSettings": {
        "serverName": "$DOMAIN",
        "alpn": ["http/1.1", "h2"],
        "certificates": [
          {
            "certificateFile": "$CERT_FILE",
            "keyFile": "$KEY_FILE"
          }
        ]
      }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

# 生成VMESS配置
vmessConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    local alterid=`shuf -i50-80 -n1`
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "vmess",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "level": 1,
          "alterId": $alterid
        }
      ]
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

vmessKCPConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    local alterid=`shuf -i50-80 -n1`
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "vmess",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "level": 1,
          "alterId": $alterid
        }
      ]
    },
    "streamSettings": {
        "network": "mkcp",
        "kcpSettings": {
            "uplinkCapacity": 100,
            "downlinkCapacity": 100,
            "congestion": true,
            "header": {
                "type": "$HEADER_TYPE"
            },
            "seed": "$SEED"
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

vmessTLSConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "vmess",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "level": 1,
          "alterId": 0
        }
      ],
      "disableInsecureEncryption": false
    },
    "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
            "serverName": "$DOMAIN",
            "alpn": ["http/1.1", "h2"],
            "certificates": [
                {
                    "certificateFile": "$CERT_FILE",
                    "keyFile": "$KEY_FILE"
                }
            ]
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

vmessWSConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $XPORT,
    "listen": "127.0.0.1",
    "protocol": "vmess",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "level": 1,
          "alterId": 0
        }
      ],
      "disableInsecureEncryption": false
    },
    "streamSettings": {
        "network": "ws",
        "wsSettings": {
            "path": "$WSPATH",
            "headers": {
                "Host": "$DOMAIN"
            }
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

vlessTLSConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "vless",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "level": 0
        }
      ],
      "decryption": "none",
      "fallbacks": [
          {
              "alpn": "http/1.1",
              "dest": 80
          },
          {
              "alpn": "h2",
              "dest": 81
          }
      ]
    },
    "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
            "serverName": "$DOMAIN",
            "alpn": ["http/1.1", "h2"],
            "certificates": [
                {
                    "certificateFile": "$CERT_FILE",
                    "keyFile": "$KEY_FILE"
                }
            ]
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

vlessXTLSConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "vless",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "flow": "$FLOW",
          "level": 0
        }
      ],
      "decryption": "none",
      "fallbacks": [
          {
              "alpn": "http/1.1",
              "dest": 80
          },
          {
              "alpn": "h2",
              "dest": 81
          }
      ]
    },
    "streamSettings": {
        "network": "tcp",
        "security": "xtls",
        "xtlsSettings": {
            "serverName": "$DOMAIN",
            "alpn": ["http/1.1", "h2"],
            "certificates": [
                {
                    "certificateFile": "$CERT_FILE",
                    "keyFile": "$KEY_FILE"
                }
            ]
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

# 生成VLESS+WS+TLS配置
vlessWSConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $XPORT,
    "listen": "127.0.0.1",
    "protocol": "vless",
    "settings": {
        "clients": [
            {
                "id": "$uuid",
                "level": 0
            }
        ],
        "decryption": "none"
    },
    "streamSettings": {
        "network": "ws",
        "security": "none",
        "wsSettings": {
            "path": "$WSPATH",
            "headers": {
                "Host": "$DOMAIN"
            }
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

vlessKCPConfig() {
    local uuid="$(cat '/proc/sys/kernel/random/uuid')"
    cat > $CONFIG_FILE<<-EOF
{
  "inbounds": [{
    "port": $PORT,
    "protocol": "vless",
    "settings": {
      "clients": [
        {
          "id": "$uuid",
          "level": 0
        }
      ],
      "decryption": "none"
    },
    "streamSettings": {
        "streamSettings": {
            "network": "mkcp",
            "kcpSettings": {
                "uplinkCapacity": 100,
                "downlinkCapacity": 100,
                "congestion": true,
                "header": {
                    "type": "$HEADER_TYPE"
                },
                "seed": "$SEED"
            }
        }
    }
  }],
  "outbounds": [{
    "protocol": "freedom",
    "settings": {}
  },{
    "protocol": "blackhole",
    "settings": {},
    "tag": "blocked"
  }]
}
EOF
}

configXray() {
    echo "正在生成Xray配置文件..."
    mkdir -p /usr/local/xray
    if [[ "$TROJAN" = "true" ]]; then
        if [[ "$XTLS" = "true" ]]; then
            trojanXTLSConfig
        else
            trojanConfig
        fi
        return 0
    fi
    if [[ "$VLESS" = "false" ]]; then
        # VMESS + kcp
        if [[ "$KCP" = "true" ]]; then
            vmessKCPConfig
            return 0
        fi
        # VMESS
        if [[ "$TLS" = "false" ]]; then
            vmessConfig
        elif [[ "$WS" = "false" ]]; then
            # VMESS+TCP+TLS
            vmessTLSConfig
        # VMESS+WS+TLS
        else
            vmessWSConfig
        fi
    #VLESS
    else
        if [[ "$KCP" = "true" ]]; then
            vlessKCPConfig
            return 0
        fi
        # VLESS+TCP
        if [[ "$WS" = "false" ]]; then
            # VLESS+TCP+TLS
            if [[ "$XTLS" = "false" ]]; then
                vlessTLSConfig
            # VLESS+TCP+XTLS
            else
                vlessXTLSConfig
            fi
        # VLESS+WS+TLS
        else
            vlessWSConfig
        fi
    fi
    echo -e "${GREEN}Xray配置文件生成成功${PLAIN}"
}

# 安装主流程
install() {
    getData
    $PMT clean all
    [[ "$PMT" = "apt" ]] && $PMT update
    
    # 安装基础工具
    if ! $CMD_INSTALL wget vim unzip tar gcc openssl net-tools; then
        colorEcho $RED "基础工具安装失败"
        return 1
    fi
    if [[ "$PMT" = "apt" ]]; then
        if ! $CMD_INSTALL libssl-dev g++; then
            colorEcho $RED "编译环境安装失败"
            return 1
        fi
    elif [[ "$PMT" = "yum" ]]; then
        if ! $CMD_INSTALL gcc-c++ openssl-devel; then
            colorEcho $RED "编译环境安装失败"
            return 1
        fi
    fi

    # 安装Nginx
    installNginx || return 1
    
    # 配置防火墙
    setFirewall
    
    # 获取证书
    if [[ "$TLS" = "true" || "$XTLS" = "true" ]]; then
        getCert || return 1
    fi
    
    # 配置Nginx
    configNginx
    
    # 安装Xray
    colorEcho $BLUE "安装Xray..."
    getVersion
    RETVAL=$?
    
    if [[ $RETVAL -eq 0 ]]; then
        colorEcho $BLUE "Xray最新版 ${CUR_VER} 已经安装"
    elif [[ $RETVAL -eq 1 ]]; then
        colorEcho $BLUE "安装Xray ${NEW_VER} ，架构: $(archAffix)"
        echo "当前版本：${RETVAL}"
        installXrayCore || return 1
        createXrayService || return 1
    else
        return 1
    fi
    
    # 生成配置
    configXray
    
    # 设置SELinux
    setSelinux
    
    # 安装BBR
    installBBR
    
    # 启动服务
    start
    
    # 显示配置信息
    showInfo
    
    # 需要重启提示
    bbrReboot
    
    return 0
}

# BBR重启提示
bbrReboot() {
    if [[ "${INSTALL_BBR}" == "true" ]]; then
        echo
        colorEcho $YELLOW "为使BBR模块生效，系统将在30秒后重启"
        echo
        colorEcho $YELLOW "您可以按 ctrl + c 取消重启，稍后输入 ${RED}reboot${PLAIN} 重启系统"
        sleep 30
        reboot
    fi
}

# 更新Xray
update() {
    res=$(status)
    [[ $res -lt 2 ]] && {
        colorEcho $RED "Xray未安装，请先安装！"
        return 1
    }

    getVersion
    RETVAL=$?
    
    case $RETVAL in
        0)
            colorEcho $BLUE "Xray最新版 ${CUR_VER} 已经安装"
            ;;
        1)
            colorEcho $BLUE "安装Xray ${NEW_VER} ，架构: $(archAffix)"
            installXrayCore || return 1
            stop
            start
            colorEcho $GREEN "最新版Xray安装成功！"
            ;;
        *)
            colorEcho $RED "更新失败"
            return 1
            ;;
    esac
    
    return 0
}

# 卸载Xray
uninstall() {
    res=$(status)
    [[ $res -lt 2 ]] && {
        colorEcho $RED "Xray未安装，请先安装！"
        return 1
    }

    echo
    read -p "确定卸载Xray？[y/n]：" answer
    [[ "${answer,,}" != "y" ]] && return 0

    # 获取域名用于清理
    local domain=$(grep -E 'Host|serverName' $CONFIG_FILE | cut -d: -f2 | tr -d \",' ' | head -1)
    
    # 停止服务
    stop
    systemctl disable xray
    
    # 删除文件
    rm -rf /usr/local/bin/xray
    rm -rf /usr/local/etc/xray
    rm -rf /etc/systemd/system/xray.service
    
    # 清理Nginx
    if [[ "$BT" = "false" ]]; then
        systemctl disable nginx
        $CMD_REMOVE nginx
        [[ "$PMT" = "apt" ]] && $CMD_REMOVE nginx-common
        [[ -f /etc/nginx/nginx.conf.bak ]] && mv /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf
    fi
    
    # 删除站点配置
    [[ -n "$domain" ]] && rm -f "${NGINX_CONF_PATH}${domain}.conf"
    
    # 清理acme.sh
    [[ -f ~/.acme.sh/acme.sh ]] && ~/.acme.sh/acme.sh --uninstall
    
    colorEcho $GREEN "Xray卸载成功"
    return 0
}

# 启动服务
start() {
    [[ ! -f /usr/local/bin/xray ]] && {
        colorEcho $RED "Xray未安装，请先安装！"
        return 1
    }
    
    res=$(status)
    [[ $res -lt 2 ]] && {
        colorEcho $RED "Xray未安装，请先安装！"
        return 1
    }
    
    stopNginx
    startNginx
    systemctl restart xray
    sleep 2
    
    port=$(grep port $CONFIG_FILE | head -n 1 | cut -d: -f2 | tr -d \",' ')
    if ss -nutlp | grep -q ":${port} .*xray"; then
        colorEcho $GREEN "Xray启动成功"
    else
        colorEcho $RED "Xray启动失败，请检查日志或查看端口是否被占用！"
        return 1
    fi
    
    return 0
}

# 停止服务
stop() {
    stopNginx
    systemctl stop xray
    colorEcho $BLUE "Xray停止成功"
    return 0
}

# 重启服务
restart() {
    if [[ ! -f $CONFIG_FILE ]] || [[ ! -f /usr/local/bin/xray ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi

    stop
    start
}

# ## socks5 install function start
installSocks5CheckAndInstall() {
    if [[ ! -f $CONFIG_FILE ]]; then
        colorEcho $RED " 请先安装1号(VMESS+WS+TLS)或8号(VLESS+XTLS)协议！"
        return 1
    fi

    cfgstr=$(cat $CONFIG_FILE)
    if echo "$cfgstr" | grep -q '"protocol": "vmess"' && echo "$cfgstr" | grep -q '"network": "ws"'; then
        base_type="vmessws"
    elif echo "$cfgstr" | grep -q '"protocol": "vless"' && echo "$cfgstr" | grep -q '"security": "xtls"'; then
        base_type="vlessxtls"
    else
        colorEcho $RED " 只支持1号(WS+VMESS+TLS)或8号(VLESS+XTLS)协议搭配SOCKS5，其它协议不可加SOCKS5！"
        return 1
    fi

    if grep -q '"protocol": "socks"' $CONFIG_FILE; then
        colorEcho $YELLOW " 已安装SOCKS5，无需重复安装"
        return 1
    fi

    echo
    read -p " 请输入SOCKS5监听端口 [默认10800]：" socks_port
    [[ -z "$socks_port" ]] && socks_port=10800

    # 检查端口是否已被占用
    if ss -tuln | grep -q ":$socks_port "; then
        colorEcho $RED " 错误：端口 $socks_port 已被其他进程占用！"
        return 1
    fi
    
    # 检查端口是否在1-65535范围内
    if [[ $socks_port -lt 1 || $socks_port -gt 65535 ]]; then
        colorEcho $RED " 错误：端口号必须在 1-65535 范围内！"
        return 1
    fi
    
    # 监听地址0.0.0.0
    [[ -z "$socks_ip" ]] && socks_ip="0.0.0.0"

    echo
    echo -e " 是否开启账号密码认证？"
    read -p " [y/N]：" need_auth
    if [[ "${need_auth,,}" = "y" ]]; then
        while true; do
            read -p " 请输入SOCKS5用户名：" socks_user
            [[ -z "$socks_user" ]] && echo " 用户名不能为空！" && continue
            break
        done
        while true; do
            read -p " 请输入SOCKS5密码：" socks_pass
            [[ -z "$socks_pass" ]] && echo " 密码不能为空！" && continue
            break
        done
    else
        socks_user=""
        socks_pass=""
    fi

    addSocks5Inbound "$socks_port" "$socks_ip" "$socks_user" "$socks_pass"
    systemctl restart xray
    sleep 2
    colorEcho $GREEN " SOCKS5安装完成！"
    # 防火墙配置
    colorEcho $BLUE " 正在配置防火墙放行端口 $socks_port..."
    if command -v firewall-cmd &>/dev/null; then
        firewall-cmd --permanent --add-port=$socks_port/tcp
        firewall-cmd --permanent --add-port=$socks_port/udp
        if [ $? -eq 0 ]; then
            firewall-cmd --reload
            colorEcho $GREEN " Firewalld 已放行端口 $socks_port"
        else
            colorEcho $RED " Firewalld 端口放行失败！请手动检查"
        fi
        
    elif command -v ufw &>/dev/null; then
        ufw allow $socks_port/tcp
        ufw allow $socks_port/udp
        if [ $? -eq 0 ]; then
            colorEcho $GREEN " UFW 已放行端口 $socks_port"
        else
            colorEcho $RED " UFW 端口放行失败！请手动检查"
        fi
        
    else
        iptables -I INPUT -p tcp --dport $socks_port -j ACCEPT
        iptables -I INPUT -p udp --dport $socks_port -j ACCEPT
        if [ $? -eq 0 ]; then
            # iptables持久化
            colorEcho $GREEN " iptables 已临时放行端口 $socks_port"
            colorEcho $YELLOW " 注意：iptables规则重启后会失效，请执行以下命令持久化："
            echo -e "   ${GREEN}Debian/Ubuntu:${PLAIN} apt install iptables-persistent -y && netfilter-persistent save"
            echo -e "   ${GREEN}CentOS/RHEL:${PLAIN} yum install iptables-services -y && service iptables save"
        else
            colorEcho $RED " iptables 端口放行失败！请手动检查"
        fi
    fi
    colorEcho $GREEN " SOCKS5安装完成！"
    showInfo
}
# ## socks5 install function end

addSocks5Inbound() {
    local port="$1"
    local addr="$2"
    local user="$3"
    local pass="$4"

    if [[ -n "$user" && -n "$pass" ]]; then
        jq '.inbounds += [{"port": '"$port"',"listen": "'"$addr"'","protocol": "socks","settings": {"auth": "password","accounts": [{"user": "'"$user"'","pass": "'"$pass"'"}], "udp": true}}]' "$CONFIG_FILE" > /tmp/xray_config_new && mv /tmp/xray_config_new "$CONFIG_FILE"
    else
        jq '.inbounds += [{"port": '"$port"',"listen": "'"$addr"'","protocol": "socks","settings": {"auth": "noauth", "udp": true}}]' "$CONFIG_FILE" > /tmp/xray_config_new && mv /tmp/xray_config_new "$CONFIG_FILE"
    fi
}

find_main_inbound_index() {
    jq -r '
        .inbounds | to_entries[] | 
        select((.value.protocol == "vmess") or 
            (.value.protocol == "vless") or 
            (.value.protocol == "trojan")) | 
        .key
    ' "$CONFIG_FILE" | head -n1
}

getConfigFileInfo() {
    # 用 jq 提取，不再多段 grep
    PROTOCOL=$(jq -r '.inbounds[0].protocol // empty' "$CONFIG_FILE")
    UUID=$(jq -r '.inbounds[0].settings.clients[0].id // empty' "$CONFIG_FILE")
    PROTOCOL=$(jq -r '.inbounds[0].protocol // empty' "$CONFIG_FILE")
    UUID=$(jq -r '.inbounds[0].settings.clients[0].id // empty' "$CONFIG_FILE")
    PASSWORD=$(jq -r '.inbounds[0].settings.clients[0].password // empty' "$CONFIG_FILE")
    ALTERID=$(jq -r '.inbounds[0].settings.clients[0].alterId // empty' "$CONFIG_FILE")
    FLOW=$(jq -r '.inbounds[0].settings.clients[0].flow // empty' "$CONFIG_FILE")
    NETWORK=$(jq -r '.inbounds[0].streamSettings.network // "tcp"' "$CONFIG_FILE")
    HOST=$(jq -r '.inbounds[0].streamSettings.wsSettings.headers.Host // empty' "$CONFIG_FILE")
    WSPATH=$(jq -r '.inbounds[0].streamSettings.wsSettings.path // empty' "$CONFIG_FILE")
    TYPE=$(jq -r '.inbounds[0].streamSettings.kcpSettings.header.type // empty' "$CONFIG_FILE")
    SEED=$(jq -r '.inbounds[0].streamSettings.kcpSettings.seed // empty' "$CONFIG_FILE")
    TLS=$(jq -r '.inbounds[0].streamSettings.security // empty' "$CONFIG_FILE")
    DOMAIN="$HOST"
    [[ -z "$DOMAIN" ]] && DOMAIN=$(jq -r '.inbounds[0].streamSettings.tlsSettings.serverName // empty' "$CONFIG_FILE")
    [[ -z "$DOMAIN" ]] && DOMAIN=$(jq -r '.inbounds[0].streamSettings.xtlsSettings.serverName // empty' "$CONFIG_FILE")
    [[ -z "$DOMAIN" ]] && DOMAIN="$IP"
    [[ -z "$DOMAIN" ]] && DOMAIN=$(hostname -I | awk '{print $1}') # fallback到本机IP
    # 端口处理（WS 场景反向代理用443，普通用实际端口）
    if [[ "$NETWORK" == "ws" ]]; then
        if [ -n "$DOMAIN" ] && [ -f "${NGINX_CONF_PATH}${DOMAIN}.conf" ]; then
            PORT=$(awk '/listen.*ssl/{print $2}' ${NGINX_CONF_PATH}${DOMAIN}.conf 2>/dev/null | head -1)
        fi
        [[ -z "$PORT" ]] && PORT=443
    else
        PORT=$(jq -r '.inbounds[0].port' "$CONFIG_FILE")
    fi
    case "$PROTOCOL" in
        "trojan")
            TLS="tls"
            [[ -n "$FLOW" ]] && TLS="xtls"
            ;;
        "vless")
            TLS=$(jq -r '.inbounds[0].streamSettings.security // "none"' "$CONFIG_FILE")
            ;;
        "vmess")
            if [[ "$NETWORK" == "ws" ]]; then
                TLS="tls"
            else
                TLS=$(jq -r '.inbounds[0].streamSettings.security // "none"' "$CONFIG_FILE")
            fi
            ;;
    esac
    #REMARK="$DOMAIN"
}

gen_node_link() {
    case "$PROTOCOL" in
    "vmess")
    raw="{
  \"v\":\"2\",
  \"ps\":\"\",
  \"add\":\"$IP\",
  \"port\":\"$PORT\",
  \"id\":\"$UUID\",
  \"aid\":\"${ALTERID:-0}\",
  \"net\":\"$NETWORK\",
  \"type\":\"$TYPE\",
  \"host\":\"$DOMAIN\",
  \"path\":\"$WSPATH\",
  \"tls\":\"${TLS/tls/tls}\"
}"
        echo "vmess://$(echo -n "$raw" | base64 -w 0)"
        ;;
    "vless")
        if [[ "$xtls" = "true" ]]; then
            echo "vless://${UUID}@${IP}:${PORT}?encryption=none&type=tcp&security=xtls&flow=${FLOW}&sni=${DOMAIN}#${REMARK}"
        elif [[ "$kcp" = "true" ]]; then
            echo "vless://${UUID}@${IP}:${PORT}?encryption=none&type=kcp&headerType=${TYPE}&seed=${SEED}#${REMARK}"
        elif [[ "$ws" = "false" ]]; then
            echo "vless://${UUID}@${IP}:${PORT}?encryption=none&type=tcp&security=tls&sni=${DOMAIN}#${REMARK}"
        else
            echo "vless://${UUID}@${IP}:${PORT}?encryption=none&type=ws&security=tls&host=${DOMAIN}&path=${WSPATH}#${REMARK}"
        fi
        echo "${xtls}"
        ;;
    "trojan")
        if [[ "$xtls" = "true" ]]; then
            echo "trojan://${PASSWORD}@${DOMAIN}:${PORT}?flow=${FLOW}&encryption=none&type=${NETWORK}&security=xtls#${REMARK}"
        else
            echo "trojan://$PASSWORD@$DOMAIN:${PORT}?type=${NETWORK}&security=tls#${REMARK}"
        fi
        ;;
    *)
        echo "暂不支持该协议: $PROTOCOL"
        ;;
    esac
}

outputSocks5() {
    # 判断 socks 协议是否存在，填充 link2
    socks_exists=$(jq -r '.inbounds[] | select(.protocol == "socks") | .protocol' "$CONFIG_FILE")
    link2=""
    if [[ "$socks_exists" == "socks" ]]; then
        port=$(jq -r '.inbounds[] | select(.protocol == "socks") | .port' "$CONFIG_FILE")
        listen=$(jq -r '.inbounds[] | select(.protocol == "socks") | .listen // "127.0.0.1"' "$CONFIG_FILE")
        auth=$(jq -r '.inbounds[] | select(.protocol == "socks") | .settings.auth // "noauth"' "$CONFIG_FILE")
        user=$(jq -r '.inbounds[] | select(.protocol == "socks") | .settings.accounts[0].user // empty' "$CONFIG_FILE")
        pass=$(jq -r '.inbounds[] | select(.protocol == "socks") | .settings.accounts[0].pass // empty' "$CONFIG_FILE")
        echo
        colorEcho $BLUE " SOCKS5配置信息："
        echo -e "   ${BLUE}监听地址: ${PLAIN}${RED}${IP}${PLAIN}"
        echo -e "   ${BLUE}监听端口: ${PLAIN}${RED}${port}${PLAIN}"
        if [[ "$auth" == "password" && -n "$user" && -n "$pass" ]]; then
            link2="socks://${user}:${pass}@${IP}:${port}"
            echo -e "   ${BLUE}认证方式: ${PLAIN}${RED}账号密码${PLAIN}"
            echo -e "   ${BLUE}用户名:   ${PLAIN}${RED}${user}${PLAIN}"
            echo -e "   ${BLUE}密码:     ${PLAIN}${RED}${pass}${PLAIN}"
            echo
            echo -e "   ${BLUE}socks链接：${PLAIN} ${RED}${link2}${PLAIN}"
        else
            link2="socks://${IP}:${port}"
            echo -e "   ${BLUE}认证方式: ${PLAIN}${RED}无认证${PLAIN}"
            echo
            echo -e "   ${BLUE}socks链接：${PLAIN}${RED}${link2}${PLAIN}"
        fi
    fi
    # 生成二维码
    if command -v qrencode >/dev/null 2>&1; then
        echo
        echo "   [${prefix}二维码如下，可用扫码工具/小火箭扫码导入]:"
        echo
        echo -n "$link" | qrencode -o - -t utf8
        echo
        if [[ -n "$link2" ]]; then
            echo
            echo "   [SOCKS二维码如下，可用扫码工具/小火箭扫码导入]:"
            echo
            echo -n "$link2" | qrencode -o - -t utf8
            echo
        fi
    else
        echo "(未检测到qrencode, 请安装: apt install -y qrencode)"
    fi
}

showInfo() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi
    
    echo ""
    echo -n -e " ${BLUE}Xray运行状态：${PLAIN}"
    statusText
    echo -e " ${BLUE}Xray配置文件: ${PLAIN} ${RED}${CONFIG_FILE}${PLAIN}"
    colorEcho $BLUE " Xray配置信息："
    getConfigFileInfo
    echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${PORT}${PLAIN}"
    [[ -n "$UUID" ]] && echo -e "   ${BLUE}id(uuid): ${PLAIN}${RED}${UUID}${PLAIN}"
    [[ -n "$ALTERID" ]] && echo -e "   ${BLUE}额外id(alterid): ${PLAIN}${RED}${ALTERID}${PLAIN}"
    [[ -n "$FLOW" ]] && echo -e "   ${BLUE}流控(flow): ${PLAIN}${RED}${FLOW}${PLAIN}"
    [[ -n "$SECURITY" ]] && echo -e "   ${BLUE}加密方式(security): ${PLAIN}${RED}${SECURITY}${PLAIN}"
    [[ -n "$ENCRYPTION" ]] && echo -e "   ${BLUE}加密(encryption): ${PLAIN}${RED}${ENCRYPTION}${PLAIN}"
    [[ -n "$NETWORK" ]] && echo -e "   ${BLUE}传输协议(network): ${PLAIN}${RED}${NETWORK}${PLAIN}"
    [[ -n "$TYPE" ]] && echo -e "   ${BLUE}伪装类型(type): ${PLAIN}${RED}${TYPE}${PLAIN}"
    [[ -n "$SEED" ]] && echo -e "   ${BLUE}mkcp seed: ${PLAIN}${RED}${SEED}${PLAIN}"
    [[ -n "$HOST" ]] && echo -e "   ${BLUE}伪装域名/主机名(host)/SNI/peer名称: ${PLAIN}${RED}${HOST}${PLAIN}"
    [[ -n "$WSPATH" ]] && echo -e "   ${BLUE}路径(path): ${PLAIN}${RED}${WSPATH}${PLAIN}"
    [[ -n "$TLS" ]] && echo -e "   ${BLUE}底层安全传输(tls): ${PLAIN}${RED}${TLS}${PLAIN}"
    [[ -n "$REMARK" ]] && echo -e "   ${BLUE}备注(remark): ${PLAIN}${RED}${REMARK}${PLAIN}"

    echo
    local link
    link="$(gen_node_link)"
    prefix=${link%%:*}
    echo -e "   ${BLUE}${prefix}链接: ${PLAIN}${RED}${link}${PLAIN}"
    # 可选生成二维码
    outputSocks5
}

# 显示日志
showLog() {
    res=$(status)
    [[ $res -lt 2 ]] && {
        colorEcho $RED "Xray未安装，请先安装！"
        return 1
    }
    
    journalctl -xen -u xray --no-pager
    return 0
}

# 主菜单
menu() {
    clear
    echo "#############################################################"
    echo -e "#                   ${RED}xray一键安装脚本${PLAIN}                        #"
    echo -e "# ${GREEN}作者${PLAIN}: 3000mall(CPLA_54J)                                  #"
    echo -e "# ${GREEN}网址${PLAIN}: https://3000mall.com                                #"
    echo -e "# ${GREEN}论坛${PLAIN}: https://bbs.3000mall.com                            #"
    echo -e "# ${GREEN}TG群${PLAIN}: https://t.me/3000mallclub                           #"
    echo -e "# ${RED}注意${PLAIN}: 本脚本仅内部，请不要外传，谢谢！                    #"
    echo -e "#                                                           #"	
    echo "#############################################################"
    echo
    echo -e "  ${GREEN}1.${PLAIN}   安装Xray-${BLUE}VMESS+WS+TLS${PLAIN}${RED}(推荐)${PLAIN}"
    echo -e "  ${GREEN}2.${PLAIN}   安装Xray-${BLUE}VMESS+mKCP${PLAIN}"
    echo -e "  ${GREEN}3.${PLAIN}   安装Xray-VMESS+TCP+TLS"
    echo -e "  ${GREEN}4.${PLAIN}   安装Xray-VMESS"
    echo -e "  ${GREEN}5.${PLAIN}   安装Xray-${BLUE}VLESS+mKCP${PLAIN}"
    echo -e "  ${GREEN}6.${PLAIN}   安装Xray-VLESS+TCP+TLS"
    echo -e "  ${GREEN}7.${PLAIN}   安装Xray-${BLUE}VLESS+WS+TLS${PLAIN}${RED}(可过cdn)${PLAIN}"
    echo -e "  ${GREEN}8.${PLAIN}   安装Xray-${BLUE}VLESS+TCP+XTLS${PLAIN}${RED}(推荐)${PLAIN}"
    echo -e "  ${GREEN}9.${PLAIN}   安装${BLUE}trojan${PLAIN}${RED}(推荐)${PLAIN}"
    echo -e "  ${GREEN}10.${PLAIN}  安装${BLUE}trojan+XTLS${PLAIN}${RED}(推荐)${PLAIN}"
    echo -e "  ${GREEN}11.${PLAIN}  安装${BLUE}SOCKS5${PLAIN}${RED}(仅可与方案1或8共存)${PLAIN}"
    echo " -------------"
    echo -e "  ${GREEN}12.${PLAIN}  更新Xray"
    echo -e "  ${GREEN}13.  ${RED}卸载Xray${PLAIN}"
    echo " -------------"
    echo -e "  ${GREEN}14.${PLAIN}  启动Xray"
    echo -e "  ${GREEN}15.${PLAIN}  重启Xray"
    echo -e "  ${GREEN}16.${PLAIN}  停止Xray"
    echo " -------------"
    echo -e "  ${GREEN}17.${PLAIN}  查看Xray配置及二维码"
    echo -e "  ${GREEN}18.${PLAIN}  查看Xray日志"
    echo " -------------"
    echo -e "  ${GREEN}0.${PLAIN}   退出"
    echo
    echo -n " 当前状态："
    statusText
    echo

    while true; do
        read -p " 请选择操作[0-18]：" answer
        case $answer in
            0) exit 0 ;;
            1) TLS="true"; WS="true"; install ;;
            2) KCP="true"; install ;;
            3) TLS="true"; install ;;
            4) install ;;
            5) VLESS="true"; KCP="true"; install ;;
            6) VLESS="true"; TLS="true"; install ;;
            7) VLESS="true"; TLS="true"; WS="true"; install ;;
            8) VLESS="true"; TLS="true"; XTLS="true"; install ;;
            9) TROJAN="true"; TLS="true"; install ;;
            10) TROJAN="true"; TLS="true"; XTLS="true"; install ;;
            11) installSocks5CheckAndInstall ;;
            12) update ;;
            13) uninstall ;;
            14) start ;;
            15) restart ;;
            16) stop ;;
            17) showInfo ;;
            18) showLog ;;
            *) colorEcho $RED " 请选择正确的操作！" ;;
        esac
        [[ $? -eq 0 ]] && break
        echo && read -p "按回车键返回主菜单..." </dev/tty
        menu
    done
}

# 主入口
main() {
    checkSystem
    getPublicIP
    detectBT
    
    case "$1" in
        menu|update|uninstall|start|restart|stop|showInfo|showLog|showQR)
            $1
            ;;
        *)
            menu
            ;;
    esac
}

main "$@"
