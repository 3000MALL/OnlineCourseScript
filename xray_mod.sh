#!/bin/bash
# xray一键安装脚本
# Author: 3000mall<wechat:CPLA_54J>

RED="\033[31m"      # Error message
GREEN="\033[32m"    # Success message
YELLOW="\033[33m"   # Warning message
BLUE="\033[36m"     # Info message
PLAIN='\033[0m'

colorEcho() {
    echo -e "${1}${@:2}${PLAIN}"
}

# 以下网站是随机从Google上找到的无广告小说网站，不喜欢请改成其他网址，以http或https开头
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

CONFIG_FILE="/usr/local/etc/xray/config.json"
OS=`hostnamectl | grep -i system | cut -d: -f2`

V6_PROXY=""
IP=`curl -sL -4 ip.sb`
if [[ "$?" != "0" ]]; then
    IP=`curl -sL -6 ip.sb`
    V6_PROXY="https://gh.3000mall.com/"
fi

BT="false"
NGINX_CONF_PATH="/etc/nginx/conf.d/"
res=`which bt 2>/dev/null`
if [[ "$res" != "" ]]; then
    BT="true"
    NGINX_CONF_PATH="/www/server/panel/vhost/nginx/"
fi

VLESS="false"
TROJAN="false"
TLS="false"
WS="false"
XTLS="false"
KCP="false"

checkSystem() {

    # 检查root权限
    if [[ $EUID -ne 0 ]]; then
        colorEcho $RED " 请以root身份执行该脚本"
        exit 1
    fi

    # 检查包管理器，并设置命令
    if command -v yum >/dev/null 2>&1; then
        PMT="yum"
        CMD_INSTALL="yum install -y "
        CMD_REMOVE="yum remove -y "
        CMD_UPGRADE="yum update -y"
    elif command -v apt >/dev/null 2>&1; then
        PMT="apt"
        CMD_INSTALL="apt install -y "
        CMD_REMOVE="apt remove -y "
        CMD_UPGRADE="apt update && apt upgrade -y && apt autoremove -y"
    else
        colorEcho $RED " 不受支持的Linux系统 (仅支持基于 Yum 或 Apt 的系统)"
        exit 1
    fi

    # 检查 systemctl
    if ! command -v systemctl >/dev/null 2>&1; then
        colorEcho $RED " 系统版本过低或未安装 systemd，请升级到最新版本"
        exit 1
    fi

    # 检查并安装 qrencode
    if ! command -v qrencode >/dev/null 2>&1; then
        colorEcho $YELLOW " qrencode 未安装，正在为你安装..."
        $CMD_INSTALL qrencode
        if ! command -v qrencode >/dev/null 2>&1; then
            colorEcho $RED " qrencode 安装失败，请手动安装后再运行脚本。"
            exit 1
        fi
    fi

    # 检查并安装 jq
    if ! command -v jq >/dev/null 2>&1; then
        colorEcho $YELLOW " jq 未安装，正在为你安装..."
        $CMD_INSTALL jq
        if ! command -v jq >/dev/null 2>&1; then
            colorEcho $RED " jq 安装失败！请手动安装后重试。"
            exit 1
        fi
    fi
}

configNeedNginx() {
    local ws=`grep wsSettings $CONFIG_FILE`
    if [[ -z "$ws" ]]; then
        echo no
        return
    fi
    echo yes
}

needNginx() {
    if [[ "$WS" = "false" ]]; then
        echo no
        return
    fi
    echo yes
}

status() {
    if [[ ! -f /usr/local/bin/xray ]]; then
        echo 0
        return
    fi
    if [[ ! -f $CONFIG_FILE ]]; then
        echo 1
        return
    fi
    port=`grep port $CONFIG_FILE| head -n 1| cut -d: -f2| tr -d \",' '`
    res=`ss -nutlp| grep ${port} | grep -i xray`
    if [[ -z "$res" ]]; then
        echo 2
        return
    fi

    if [[ `configNeedNginx` != "yes" ]]; then
        echo 3
    else
        res=`ss -nutlp|grep -i nginx`
        if [[ -z "$res" ]]; then
            echo 4
        else
            echo 5
        fi
    fi
}

statusText() {
    res=`status`
    case $res in
        2)
            echo -e ${GREEN}已安装${PLAIN} ${RED}未运行${PLAIN}
            ;;
        3)
            echo -e ${GREEN}已安装${PLAIN} ${GREEN}Xray正在运行${PLAIN}
            ;;
        4)
            echo -e ${GREEN}已安装${PLAIN} ${GREEN}Xray正在运行${PLAIN}, ${RED}Nginx未运行${PLAIN}
            ;;
        5)
            echo -e ${GREEN}已安装${PLAIN} ${GREEN}Xray正在运行, Nginx正在运行${PLAIN}
            ;;
        *)
            echo -e ${RED}未安装${PLAIN}
            ;;
    esac
}

normalizeVersion() {
    if [ -n "$1" ]; then
        case "$1" in
            v*)
                echo "$1"
            ;;
            http*)
                echo "v1.4.2"
            ;;
            *)
                echo "v$1"
            ;;
        esac
    else
        echo ""
    fi
}

# 1: new Xray. 0: no. 1: yes. 2: not installed. 3: check failed.
getVersion() {
    VER=`/usr/local/bin/xray version|head -n1 | awk '{print $2}'`
    RETVAL=$?
    CUR_VER="$(normalizeVersion "$(echo "$VER" | head -n 1 | cut -d " " -f2)")"
    TAG_URL="${V6_PROXY}https://api.github.com/repos/XTLS/Xray-core/releases/latest"
    NEW_VER="$(normalizeVersion "$(curl -s "${TAG_URL}" --connect-timeout 10| grep 'tag_name' | cut -d\" -f4)")"

    if [[ $? -ne 0 ]] || [[ $NEW_VER == "" ]]; then
        colorEcho $RED " 检查Xray版本信息失败，请检查网络"
        return 3
    elif [[ $RETVAL -ne 0 ]];then
        return 2
    elif [[ $NEW_VER != $CUR_VER ]];then
        return 1
    fi
    return 0
}

archAffix(){
    case "$(uname -m)" in
        x86_64 | x64 | amd64 ) echo 'amd64' ;;
        i*86 | x86 ) echo '386' ;;
        armv8* | armv8 | arm64 | aarch64 ) echo 'arm64' ;;
        armv7* | armv7 | arm ) echo 'armv7' ;;
        armv6* | armv6 ) echo 'armv6' ;;
        armv5* | armv5 ) echo 'armv5' ;;
        armv5* | armv5 ) echo 's390x' ;;
        *) echo -e "${green}不支持的CPU架构! ${plain}" && rm -f install.sh && exit 1 ;;
    esac
}

getData() {
    if [[ "$TLS" = "true" || "$XTLS" = "true" ]]; then
        echo ""
        echo " Xray一键脚本，运行之前请确认如下条件已经具备：(不懂可以微信联系我：3000mall)"
        colorEcho ${YELLOW} "  1. 一个伪装域名"
        colorEcho ${YELLOW} "  2. 伪装域名DNS解析指向当前服务器ip（${IP}）"
        colorEcho ${BLUE} "  3. 如果/root目录下有 xray.pem 和 xray.key 证书密钥文件，无需理会条件2"
        echo " "
        read -p " 确认满足按y，按其他退出脚本：" answer
        if [[ "${answer,,}" != "y" ]]; then
            exit 0
        fi

        echo ""
	
	# 授权域名列表
	ALLOWED_DOMAINS=("ciuok.com" "dimsn.com" "hhgtk.com")
    
	while true
	do
	    read -p " 请输入伪装域名：" DOMAIN
	    DOMAIN=$(echo "$DOMAIN" | tr '[:upper:]' '[:lower:]')  # 转换为小写
	    DOMAIN="${DOMAIN%.}"  # 去除末尾可能的点
	    if [[ -z "${DOMAIN}" ]]; then
	        colorEcho ${RED} " 域名不能为空，请重新输入！"
	    else
	        valid=0
	        for allowed in "${ALLOWED_DOMAINS[@]}"; do
	            if [[ "$DOMAIN" == "$allowed" || "$DOMAIN" =~ \."$allowed"$ ]]; then
	                valid=1
	                break
	            fi
	        done
            if [[ $valid -eq 1 ]]; then
                # 新增一个死循环，直到解析到当前服务器IP为止
                while true; do
                    if [[ -f ~/xray.pem && -f ~/xray.key ]]; then
                        colorEcho ${BLUE}  " 检测到自有证书，将使用其部署"
                        CERT_FILE="/usr/local/etc/xray/${DOMAIN}.pem"
                        KEY_FILE="/usr/local/etc/xray/${DOMAIN}.key"
                        break 2
                    else
                        resolve=`curl -sL http://ip-api.com/json/${DOMAIN}`
                        res=`echo -n ${resolve} | grep ${IP}`
                        if [[ -z "${res}" ]]; then
                            colorEcho ${BLUE}  "${DOMAIN} 解析结果：${resolve}"
                            colorEcho ${RED}  " 域名未解析到当前服务器IP(${IP})!"
                            colorEcho ${RED}  " 请确保域名已正确解析，并尽量稍等1-2分钟（DNS生效），然后重新输入域名。"
                            read -p " 按回车重新输入域名..." IGNORE
                            # 重新外层循环重新输入域名
                            break
                        else
                            # 域名解析正确，跳出两层循环
                            break 2
                        fi
                    fi
                done
            else
	            colorEcho ${RED} " 当前域名未授权使用，请微信联系3000mall！"
	        fi
	    fi
	done
        DOMAIN=${DOMAIN,,}
        colorEcho ${BLUE}  " 伪装域名(host)：$DOMAIN"
    fi

    echo ""
    if [[ "$(needNginx)" = "no" ]]; then
        if [[ "$TLS" = "true" ]]; then
            read -p " 请输入xray监听端口[强烈建议443，默认443]：" PORT
            [[ -z "${PORT}" ]] && PORT=443
        else
            read -p " 请输入xray监听端口[100-65535的一个数字]：" PORT
            [[ -z "${PORT}" ]] && PORT=`shuf -i200-65000 -n1`
            if [[ "${PORT:0:1}" = "0" ]]; then
                colorEcho ${RED}  " 端口不能以0开头"
                exit 1
            fi
        fi
        colorEcho ${BLUE}  " xray端口：$PORT"
    else
        read -p " 请输入Nginx监听端口[100-65535的一个数字，默认443]：" PORT
        [[ -z "${PORT}" ]] && PORT=443
        if [ "${PORT:0:1}" = "0" ]; then
            colorEcho ${BLUE}  " 端口不能以0开头"
            exit 1
        fi
        colorEcho ${BLUE}  " Nginx端口：$PORT"
        XPORT=`shuf -i10000-65000 -n1`
    fi

    if [[ "$KCP" = "true" ]]; then
        echo ""
        colorEcho $BLUE " 请选择伪装类型："
        echo "   1) 无"
        echo "   2) BT下载"
        echo "   3) 视频通话"
        echo "   4) 微信视频通话"
        echo "   5) dtls"
        echo "   6) wiregard"
        read -p "  请选择伪装类型[默认：无]：" answer
        case $answer in
            2)
                HEADER_TYPE="utp"
                ;;
            3)
                HEADER_TYPE="srtp"
                ;;
            4)
                HEADER_TYPE="wechat-video"
                ;;
            5)
                HEADER_TYPE="dtls"
                ;;
            6)
                HEADER_TYPE="wireguard"
                ;;
            *)
                HEADER_TYPE="none"
                ;;
        esac
        colorEcho $BLUE " 伪装类型：$HEADER_TYPE"
        SEED=`cat /proc/sys/kernel/random/uuid`
    fi

    if [[ "$TROJAN" = "true" ]]; then
        echo ""
        read -p " 请设置trojan密码（不输则随机生成）:" PASSWORD
        [[ -z "$PASSWORD" ]] && PASSWORD=`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1`
        colorEcho $BLUE " trojan密码：$PASSWORD"
    fi

    if [[ "$XTLS" = "true" ]]; then
        echo ""
        colorEcho $BLUE " 请选择流控模式:" 
        echo -e "   1) xtls-rprx-direct [$RED推荐$PLAIN]"
        echo "   2) xtls-rprx-origin"
        read -p "  请选择流控模式[默认:direct]" answer
        [[ -z "$answer" ]] && answer=1
        case $answer in
            1)
                FLOW="xtls-rprx-direct"
                ;;
            2)
                FLOW="xtls-rprx-origin"
                ;;
            *)
                colorEcho $RED " 无效选项，使用默认的xtls-rprx-direct"
                FLOW="xtls-rprx-direct"
                ;;
        esac
        colorEcho $BLUE " 流控模式：$FLOW"
    fi

    if [[ "${WS}" = "true" ]]; then
        echo ""
        while true
        do
            read -p " 请输入伪装路径，以/开头(不懂请直接回车)：" WSPATH
            if [[ -z "${WSPATH}" ]]; then
                len=`shuf -i5-12 -n1`
                ws=`cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $len | head -n 1`
                WSPATH="/$ws"
                break
            elif [[ "${WSPATH:0:1}" != "/" ]]; then
                colorEcho ${RED}  " 伪装路径必须以/开头！"
            elif [[ "${WSPATH}" = "/" ]]; then
                colorEcho ${RED}   " 不能使用根路径！"
            else
                break
            fi
        done
        colorEcho ${BLUE}  " ws路径：$WSPATH"
    fi

    if [[ "$TLS" = "true" || "$XTLS" = "true" ]]; then
        echo ""
        colorEcho $BLUE " 请选择伪装站类型:"
        echo "   1) 静态网站(位于/usr/share/nginx/html)"
        echo "   2) 小说站(随机选择)"
        echo "   3) 美女站(https://imeizi.me)"
        echo "   4) 高清壁纸站(https://bing.imeizi.me)"
        echo "   5) 自定义反代站点(需以http或者https开头)"
        read -p "  请选择伪装网站类型[默认:出海导航]" answer
        if [[ -z "$answer" ]]; then
            PROXY_URL="https://tkstart.com"
        else
            case $answer in
            1)
                PROXY_URL=""
                ;;
            2)
                len=${#SITES[@]}
                ((len--))
                while true
                do
                    index=`shuf -i0-${len} -n1`
                    PROXY_URL=${SITES[$index]}
                    host=`echo ${PROXY_URL} | cut -d/ -f3`
                    ip=`curl -sL http://ip-api.com/json/${host}`
                    res=`echo -n ${ip} | grep ${host}`
                    if [[ "${res}" = "" ]]; then
                        echo "$ip $host" >> /etc/hosts
                        break
                    fi
                done
                ;;
            3)
                PROXY_URL="https://imeizi.me"
                ;;
            4)
                PROXY_URL="https://bing.imeizi.me"
                ;;
            5)
                while true
                do
                    read -p " 请输入反代站点(以http或者https开头)：" PROXY_URL
                    if [[ -z "$PROXY_URL" ]]; then
                        colorEcho $RED " 请输入反代网站！"
                    elif [[ "${PROXY_URL:0:4}" != "http" ]]; then
                        colorEcho $RED " 反代网站必须以http或https开头！"
                    else
                        break
                    fi
                done
                ;;
            *)
                colorEcho $RED " 请输入正确的选项！"
                exit 1
            esac
        fi
        REMOTE_HOST=`echo ${PROXY_URL} | cut -d/ -f3`
        colorEcho $BLUE " 伪装网站：$PROXY_URL"

        echo ""
        colorEcho $BLUE "  是否允许搜索引擎爬取网站？[默认：不允许]"
        echo "    y)允许，会有更多ip请求网站，但会消耗一些流量，vps流量充足情况下推荐使用"
        echo "    n)不允许，爬虫不会访问网站，访问ip比较单一，但能节省vps流量"
        read -p "  请选择：[y/n]" answer
        if [[ -z "$answer" ]]; then
            ALLOW_SPIDER="n"
        elif [[ "${answer,,}" = "y" ]]; then
            ALLOW_SPIDER="y"
        else
            ALLOW_SPIDER="n"
        fi
        colorEcho $BLUE " 允许搜索引擎：$ALLOW_SPIDER"
    fi

    echo ""
    read -p " 是否安装BBR(默认安装)?[y/n]:" NEED_BBR
    [[ -z "$NEED_BBR" ]] && NEED_BBR=y
    [[ "$NEED_BBR" = "Y" ]] && NEED_BBR=y
    colorEcho $BLUE " 安装BBR：$NEED_BBR"
}

installNginx() {
    echo ""
    colorEcho $BLUE " 安装nginx..."
    if [[ "$BT" = "false" ]]; then
        if [[ "$PMT" = "yum" ]]; then
            $CMD_INSTALL epel-release
            if [[ "$?" != "0" ]]; then
                echo '[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true' > /etc/yum.repos.d/nginx.repo
            fi
        fi
        $CMD_INSTALL nginx
        if [[ "$?" != "0" ]]; then
            colorEcho $RED " Nginx安装失败，请到微信反馈给3000mall"
            exit 1
        fi
        systemctl enable nginx
    else
        res=`which nginx 2>/dev/null`
        if [[ "$?" != "0" ]]; then
            colorEcho $RED " 您安装了宝塔，请在宝塔后台安装nginx后再运行本脚本"
            exit 1
        fi
    fi
}

startNginx() {
    if [[ "$BT" = "false" ]]; then
        systemctl start nginx
    else
        nginx -c /www/server/nginx/conf/nginx.conf
    fi
}

stopNginx() {
    if [[ "$BT" = "false" ]]; then
        systemctl stop nginx
    else
        res=`ps aux | grep -i nginx`
        if [[ "$res" != "" ]]; then
            nginx -s stop
        fi
    fi
}

getCert() {
    mkdir -p /usr/local/etc/xray
    if [[ -z ${CERT_FILE+x} ]]; then
        stopNginx
        systemctl stop xray
        res=`netstat -ntlp| grep -E ':80 |:443 '`
        if [[ "${res}" != "" ]]; then
            colorEcho ${RED}  " 其他进程占用了80或443端口，请先关闭再运行一键脚本"
            echo " 端口占用信息如下："
            echo ${res}
            exit 1
        fi

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
        curl -sL https://get.acme.sh | sh -s email=3000mall@dimsn.com
        source ~/.bashrc
        ~/.acme.sh/acme.sh  --upgrade  --auto-upgrade
        ~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
        if [[ "$BT" = "false" ]]; then
            ~/.acme.sh/acme.sh   --issue -d $DOMAIN --keylength ec-256 --pre-hook "systemctl stop nginx" --post-hook "systemctl restart nginx"  --standalone
        else
            ~/.acme.sh/acme.sh   --issue -d $DOMAIN --keylength ec-256 --pre-hook "nginx -s stop || { echo -n ''; }" --post-hook "nginx -c /www/server/nginx/conf/nginx.conf || { echo -n ''; }"  --standalone
        fi
        [[ -f ~/.acme.sh/${DOMAIN}_ecc/ca.cer ]] || {
            colorEcho $RED " 获取证书失败，请复制上面的红色文字到 微信（3000mall） 反馈给我"
            exit 1
        }
        CERT_FILE="/usr/local/etc/xray/${DOMAIN}.pem"
        KEY_FILE="/usr/local/etc/xray/${DOMAIN}.key"
        ~/.acme.sh/acme.sh  --install-cert -d $DOMAIN --ecc \
            --key-file       $KEY_FILE  \
            --fullchain-file $CERT_FILE \
            --reloadcmd     "service nginx force-reload"
        [[ -f $CERT_FILE && -f $KEY_FILE ]] || {
            colorEcho $RED " 获取证书失败，请到 微信（3000mall） 反馈给我"
            exit 1
        }
    else
        cp ~/xray.pem /usr/local/etc/xray/${DOMAIN}.pem
        cp ~/xray.key /usr/local/etc/xray/${DOMAIN}.key
    fi
}

configNginx() {
    mkdir -p /usr/share/nginx/html;
    if [[ "$ALLOW_SPIDER" = "n" ]]; then
        echo 'User-Agent: *' > /usr/share/nginx/html/robots.txt
        echo 'Disallow: /' >> /usr/share/nginx/html/robots.txt
        ROBOT_CONFIG="    location = /robots.txt {}"
    else
        ROBOT_CONFIG=""
    fi

    if [[ "$BT" = "false" ]]; then
        if [[ ! -f /etc/nginx/nginx.conf.bak ]]; then
            mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
        fi
        res=`id nginx 2>/dev/null`
        if [[ "$?" != "0" ]]; then
            user="www-data"
        else
            user="nginx"
        fi
        cat > /etc/nginx/nginx.conf<<-EOF
user $user;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                      '\$status \$body_bytes_sent "\$http_referer" '
                      '"\$http_user_agent" "\$http_x_forwarded_for"';

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
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;
}
EOF
    fi

    if [[ "$PROXY_URL" = "" ]]; then
        action=""
    else
        action="proxy_ssl_server_name on;
        proxy_pass $PROXY_URL;
        proxy_set_header Accept-Encoding '';
        sub_filter \"$REMOTE_HOST\" \"$DOMAIN\";
        sub_filter_once off;"
    fi

    if [[ "$TLS" = "true" || "$XTLS" = "true" ]]; then
        mkdir -p ${NGINX_CONF_PATH}
        # VMESS+WS+TLS
        # VLESS+WS+TLS
        if [[ "$WS" = "true" ]]; then
            cat > ${NGINX_CONF_PATH}${DOMAIN}.conf<<-EOF
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
            # VLESS+TCP+TLS
            # VLESS+TCP+XTLS
            # trojan
            cat > ${NGINX_CONF_PATH}${DOMAIN}.conf<<-EOF
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
    fi
}

setSelinux() {
    if [[ -s /etc/selinux/config ]] && grep 'SELINUX=enforcing' /etc/selinux/config; then
        sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config
        setenforce 0
    fi
}

setFirewall() {
    res=$(which firewall-cmd 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        systemctl status firewalld > /dev/null 2>&1
        if [[ $? -eq 0 ]]; then
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            # 自动放行用户设置的端口和XPORT（有则都放，无则跳过443判断）
            if [[ -n "${PORT}" ]]; then
                firewall-cmd --permanent --add-port=${PORT}/tcp
                firewall-cmd --permanent --add-port=${PORT}/udp
            fi
            if [[ -n "${XPORT}" ]]; then
                firewall-cmd --permanent --add-port=${XPORT}/tcp
                firewall-cmd --permanent --add-port=${XPORT}/udp
            fi
            firewall-cmd --reload
        else
            nl=$(iptables -nL | nl | grep FORWARD | awk '{print $1}')
            if [[ "$nl" != "3" ]]; then
                iptables -I INPUT -p tcp --dport 80 -j ACCEPT
                iptables -I INPUT -p tcp --dport 443 -j ACCEPT
                # 放行端口
                if [[ -n "${PORT}" ]]; then
                    iptables -I INPUT -p tcp --dport ${PORT} -j ACCEPT
                    iptables -I INPUT -p udp --dport ${PORT} -j ACCEPT
                fi
                if [[ -n "${XPORT}" ]]; then
                    iptables -I INPUT -p tcp --dport ${XPORT} -j ACCEPT
                    iptables -I INPUT -p udp --dport ${XPORT} -j ACCEPT
                fi
            fi
        fi
    else
        res=$(which iptables 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            nl=$(iptables -nL | nl | grep FORWARD | awk '{print $1}')
            if [[ "$nl" != "3" ]]; then
                iptables -I INPUT -p tcp --dport 80 -j ACCEPT
                iptables -I INPUT -p tcp --dport 443 -j ACCEPT
                # 放行端口
                if [[ -n "${PORT}" ]]; then
                    iptables -I INPUT -p tcp --dport ${PORT} -j ACCEPT
                    iptables -I INPUT -p udp --dport ${PORT} -j ACCEPT
                fi
                if [[ -n "${XPORT}" ]]; then
                    iptables -I INPUT -p tcp --dport ${XPORT} -j ACCEPT
                    iptables -I INPUT -p udp --dport ${XPORT} -j ACCEPT
                fi
            fi
        else
            res=$(which ufw 2>/dev/null)
            if [[ $? -eq 0 ]]; then
                res=$(ufw status | grep -i inactive)
                if [[ "$res" = "" ]]; then
                    ufw allow http/tcp
                    ufw allow https/tcp
                    if [[ -n "${PORT}" ]]; then
                        ufw allow ${PORT}/tcp
                        ufw allow ${PORT}/udp
                    fi
                    if [[ -n "${XPORT}" ]]; then
                        ufw allow ${XPORT}/tcp
                        ufw allow ${XPORT}/udp
                    fi
                fi
            fi
        fi
    fi
}


installBBR() {
    if [[ "$NEED_BBR" != "y" ]]; then
        INSTALL_BBR=false
        return
    fi
    result=$(lsmod | grep bbr)
    if [[ "$result" != "" ]]; then
        colorEcho $BLUE " 官方原版BBR模块已安装"
        INSTALL_BBR=false
        return
    fi
    res=`hostnamectl | grep -i openvz`
    if [[ "$res" != "" ]]; then
        colorEcho $BLUE " openvz机器，跳过安装"
        INSTALL_BBR=false
        return
    fi
    
    echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    sysctl -p
    result=$(lsmod | grep bbr)
    if [[ "$result" != "" ]]; then
        colorEcho $GREEN " 官方原版BBR模块已启用"
        INSTALL_BBR=false
        return
    fi

    colorEcho $BLUE " 安装官方原版BBR模块..."
    if [[ "$PMT" = "yum" ]]; then
        if [[ "$V6_PROXY" = "" ]]; then
            rpm --import https://www.elrepo.org/RPM-GPG-KEY-elrepo.org
            rpm -Uvh http://www.elrepo.org/elrepo-release-7.0-4.el7.elrepo.noarch.rpm
            $CMD_INSTALL --enablerepo=elrepo-kernel kernel-ml
            $CMD_REMOVE kernel-3.*
            grub2-set-default 0
            echo "tcp_bbr" >> /etc/modules-load.d/modules.conf
            INSTALL_BBR=true
        fi
    else
        $CMD_INSTALL --install-recommends linux-generic-hwe-16.04
        grub-set-default 0
        echo "tcp_bbr" >> /etc/modules-load.d/modules.conf
        INSTALL_BBR=true
    fi
}

installXray() {
    rm -rf /tmp/xray
    mkdir -p /tmp/xray
    DOWNLOAD_LINK="${V6_PROXY}https://github.com/XTLS/Xray-core/releases/download/${NEW_VER}/Xray-linux-$(archAffix).zip"
    colorEcho $BLUE " 下载Xray: ${DOWNLOAD_LINK}"
    curl -L -H "Cache-Control: no-cache" -o /tmp/xray/xray.zip ${DOWNLOAD_LINK}
    if [ $? != 0 ];then
        colorEcho $RED " 下载Xray文件失败，请检查服务器网络设置"
        exit 1
    fi
    systemctl stop xray
    mkdir -p /usr/local/etc/xray /usr/local/share/xray && \
    unzip /tmp/xray/xray.zip -d /tmp/xray
    cp /tmp/xray/xray /usr/local/bin
    cp /tmp/xray/geo* /usr/local/share/xray
    chmod +x /usr/local/bin/xray || {
        colorEcho $RED " Xray安装失败"
        exit 1
    }

    cat >/etc/systemd/system/xray.service<<-EOF
[Unit]
Description=Xray Service
Documentation=https://github.com/xtls https://3000mall.com
After=network.target nss-lookup.target

[Service]
User=root
#User=nobody
#CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
#AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
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

trojanConfig() {
    cat > $CONFIG_FILE<<-EOF
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

trojanXTLSConfig() {
    cat > $CONFIG_FILE<<-EOF
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
}

install() {
    getData

    $PMT clean all
    [[ "$PMT" = "apt" ]] && $PMT update
    #echo $CMD_UPGRADE | bash
    $CMD_INSTALL wget vim unzip tar gcc openssl
    $CMD_INSTALL net-tools
    if [[ "$PMT" = "apt" ]]; then
        $CMD_INSTALL libssl-dev g++
    fi
    res=`which unzip 2>/dev/null`
    if [[ $? -ne 0 ]]; then
        colorEcho $RED " unzip安装失败，请检查网络"
        exit 1
    fi

    installNginx
    setFirewall
    if [[ "$TLS" = "true" || "$XTLS" = "true" ]]; then
        getCert
    fi
    configNginx

    colorEcho $BLUE " 安装Xray..."
    getVersion
    RETVAL="$?"
    if [[ $RETVAL == 0 ]]; then
        colorEcho $BLUE " Xray最新版 ${CUR_VER} 已经安装"
    elif [[ $RETVAL == 3 ]]; then
        exit 1
    else
        colorEcho $BLUE " 安装Xray ${NEW_VER} ，架构$(archAffix)"
        installXray
    fi

    configXray

    setSelinux
    installBBR

    start
    showInfoWithSocks5

    bbrReboot
}

bbrReboot() {
    if [[ "${INSTALL_BBR}" == "true" ]]; then
        echo  
        echo " 为使BBR模块生效，系统将在30秒后重启"
        echo  
        echo -e " 您可以按 ctrl + c 取消重启，稍后输入 ${RED}reboot${PLAIN} 重启系统"
        sleep 30
        reboot
    fi
}

update() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi

    getVersion
    RETVAL="$?"
    if [[ $RETVAL == 0 ]]; then
        colorEcho $BLUE " Xray最新版 ${CUR_VER} 已经安装"
    elif [[ $RETVAL == 3 ]]; then
        exit 1
    else
        colorEcho $BLUE " 安装Xray ${NEW_VER} ，架构$(archAffix)"
        installXray
        stop
        start

        colorEcho $GREEN " 最新版Xray安装成功！"
    fi
}

uninstall() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi

    echo ""
    read -p " 确定卸载Xray？[y/n]：" answer
    if [[ "${answer,,}" = "y" ]]; then
        domain=`grep Host $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
        if [[ "$domain" = "" ]]; then
            domain=`grep serverName $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
        fi
        
        stop
        systemctl disable xray
        rm -rf /etc/systemd/system/xray.service
        rm -rf /usr/local/bin/xray
        rm -rf /usr/local/etc/xray

        if [[ "$BT" = "false" ]]; then
            systemctl disable nginx
            $CMD_REMOVE nginx
            if [[ "$PMT" = "apt" ]]; then
                $CMD_REMOVE nginx-common
            fi
            rm -rf /etc/nginx/nginx.conf
            if [[ -f /etc/nginx/nginx.conf.bak ]]; then
                mv /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf
            fi
        fi
        if [[ "$domain" != "" ]]; then
            rm -rf ${NGINX_CONF_PATH}${domain}.conf
        fi
        [[ -f ~/.acme.sh/acme.sh ]] && ~/.acme.sh/acme.sh --uninstall
        colorEcho $GREEN " Xray卸载成功"
    fi
}

start() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi
    stopNginx
    startNginx
    systemctl restart xray
    sleep 2
    
    port=`grep port $CONFIG_FILE| head -n 1| cut -d: -f2| tr -d \",' '`
    res=`ss -nutlp| grep ${port} | grep -i xray`
    if [[ "$res" = "" ]]; then
        colorEcho $RED " Xray启动失败，请检查日志或查看端口是否被占用！"
    else
        colorEcho $BLUE " Xray启动成功"
    fi
}

stop() {
    stopNginx
    systemctl stop xray
    colorEcho $BLUE " Xray停止成功"
}


restart() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi

    stop
    start
}


getConfigFileInfo() {
    vless="false"
    tls="false"
    ws="false"
    xtls="false"
    trojan="false"
    protocol="VMess"
    kcp="false"

    uid=`grep id $CONFIG_FILE | head -n1| cut -d: -f2 | tr -d \",' '`
    alterid=`grep alterId $CONFIG_FILE  | cut -d: -f2 | tr -d \",' '`
    network=`grep network $CONFIG_FILE  | tail -n1| cut -d: -f2 | tr -d \",' '`
    [[ -z "$network" ]] && network="tcp"
    domain=`grep serverName $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
    if [[ "$domain" = "" ]]; then
        domain=`grep Host $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
        if [[ "$domain" != "" ]]; then
            ws="true"
            tls="true"
            wspath=`grep path $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
        fi
    else
        tls="true"
    fi
    if [[ "$ws" = "true" ]]; then
        port=`grep -i ssl $NGINX_CONF_PATH${domain}.conf| head -n1 | awk '{print $2}'`
    else
        port=`grep port $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
    fi
    res=`grep -i kcp $CONFIG_FILE`
    if [[ "$res" != "" ]]; then
        kcp="true"
        type=`grep header -A 3 $CONFIG_FILE | grep 'type' | cut -d: -f2 | tr -d \",' '`
        seed=`grep seed $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
    fi

    vmess=`grep vmess $CONFIG_FILE`
    if [[ "$vmess" = "" ]]; then
        trojan=`grep trojan $CONFIG_FILE`
        if [[ "$trojan" = "" ]]; then
            vless="true"
            protocol="VLESS"
        else
            trojan="true"
            password=`grep password $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
            protocol="trojan"
        fi
        tls="true"
        encryption="none"
        xtls=`grep xtlsSettings $CONFIG_FILE`
        if [[ "$xtls" != "" ]]; then
            xtls="true"
            flow=`grep flow $CONFIG_FILE | cut -d: -f2 | tr -d \",' '`
        else
            flow="无"
        fi
    fi
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

    read -p " 请输入SOCKS5监听地址 [默认127.0.0.1]：" socks_ip
    [[ -z "$socks_ip" ]] && socks_ip="127.0.0.1"

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
    showInfoWithSocks5
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

outputVmess() {
    raw="{
  \"v\":\"2\",
  \"ps\":\"\",
  \"add\":\"$IP\",
  \"port\":\"${port}\",
  \"id\":\"${uid}\",
  \"aid\":\"$alterid\",
  \"net\":\"tcp\",
  \"type\":\"none\",
  \"host\":\"\",
  \"path\":\"\",
  \"tls\":\"\"
}"
    link=`echo -n ${raw} | base64 -w 0`
    link="vmess://${link}"

    echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
    echo -e "   ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
    echo -e "   ${BLUE}额外id(alterid)：${PLAIN} ${RED}${alterid}${PLAIN}"
    echo -e "   ${BLUE}加密方式(security)：${PLAIN} ${RED}auto${PLAIN}"
    echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
    echo  
    echo -e "   ${BLUE}vmess链接:${PLAIN} $RED$link$PLAIN"
}

outputVmessKCP() {
    echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
    echo -e "   ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
    echo -e "   ${BLUE}额外id(alterid)：${PLAIN} ${RED}${alterid}${PLAIN}"
    echo -e "   ${BLUE}加密方式(security)：${PLAIN} ${RED}auto${PLAIN}"
    echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}"
    echo -e "   ${BLUE}伪装类型(type)：${PLAIN} ${RED}${type}${PLAIN}"
    echo -e "   ${BLUE}mkcp seed：${PLAIN} ${RED}${seed}${PLAIN}" 
}

outputTrojan() {
    if [[ "$xtls" = "true" ]]; then
        link="trojan://${password}@${domain}:${port}?flow=${flow}&encryption=none&type=${network}&security=xtls#${password}"
        
        echo -e "   ${BLUE}IP/域名(address): ${PLAIN} ${RED}${domain}${PLAIN}"
        echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
        echo -e "   ${BLUE}密码(password)：${PLAIN}${RED}${password}${PLAIN}"
        echo -e "   ${BLUE}流控(flow)：${PLAIN}$RED$flow${PLAIN}"
        echo -e "   ${BLUE}加密(encryption)：${PLAIN} ${RED}none${PLAIN}"
        echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}"
        echo -e "   ${BLUE}底层安全传输(tls)：${PLAIN}${RED}XTLS${PLAIN}"
        echo
        echo -e "   ${BLUE}trojan链接:${PLAIN} $RED$link$PLAIN"
    else
        link="trojan://$password@$domain:$port?type=$network&security=tls#$password"
        echo -e "   ${BLUE}IP/域名(address): ${PLAIN} ${RED}${domain}${PLAIN}"
        echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
        echo -e "   ${BLUE}密码(password)：${PLAIN}${RED}${password}${PLAIN}"
        echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
        echo -e "   ${BLUE}底层安全传输(tls)：${PLAIN}${RED}TLS${PLAIN}"
        echo
        echo -e "   ${BLUE}trojan链接:${PLAIN} $RED$link$PLAIN"
    fi
}

outputTrojanWS() {
    link="trojan://${uid}@${IP}:${port}?sni=${domain}&type=${network}&host=${domain}&path=${wspath}#${uid}"
    echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
    echo -e "   ${BLUE}密码(password)：${PLAIN}${RED}${uid}${PLAIN}"
    echo -e "   ${BLUE}传输协议(network)：${PLAIN}${RED}${network}${PLAIN}"
    echo -e "   ${BLUE}伪装域名/主机名(host)/SNI/peer名称：${PLAIN}${RED}${domain}${PLAIN}"
    echo -e "   ${BLUE}路径(path)：${PLAIN}${RED}${wspath}${PLAIN}"
    echo -e "   ${BLUE}底层安全传输(tls)：${PLAIN}${RED}TLS${PLAIN}"
    echo
    echo -e "   ${BLUE}trojan链接:${PLAIN} $RED$link$PLAIN"
}

outputTrojanXTLS() { #暂时不用
    link="trojan://${password}@${domain}:${port}?flow=${flow}&encryption=none&type=${network}&security=xtls#${password}"
    
    echo -e "   ${BLUE}IP/域名(address): ${PLAIN} ${RED}${domain}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
    echo -e "   ${BLUE}密码(password)：${PLAIN}${RED}${password}${PLAIN}"
    echo -e "   ${BLUE}流控(flow)：${PLAIN}$RED$flow${PLAIN}"
    echo -e "   ${BLUE}加密(encryption)：${PLAIN} ${RED}none${PLAIN}"
    echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}"
    echo -e "   ${BLUE}底层安全传输(tls)：${PLAIN}${RED}XTLS${PLAIN}"
    echo
    echo -e "   ${BLUE}trojan链接:${PLAIN} $RED$link$PLAIN"
}

outputVmessTLS() {
    raw="{
  \"v\":\"2\",
  \"ps\":\"\",
  \"add\":\"$IP\",
  \"port\":\"${port}\",
  \"id\":\"${uid}\",
  \"aid\":\"$alterid\",
  \"net\":\"${network}\",
  \"type\":\"none\",
  \"host\":\"${domain}\",
  \"path\":\"\",
  \"tls\":\"tls\"
}"
    link=`echo -n ${raw} | base64 -w 0`
    link="vmess://${link}"
    echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
    echo -e "   ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
    echo -e "   ${BLUE}额外id(alterid)：${PLAIN} ${RED}${alterid}${PLAIN}"
    echo -e "   ${BLUE}加密方式(security)：${PLAIN} ${RED}none${PLAIN}"
    echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
    echo -e "   ${BLUE}伪装域名/主机名(host)/SNI/peer名称：${PLAIN}${RED}${domain}${PLAIN}"
    echo -e "   ${BLUE}底层安全传输(tls)：${PLAIN}${RED}TLS${PLAIN}"
    echo  
    echo -e "   ${BLUE}vmess链接: ${PLAIN}$RED$link$PLAIN"
}

outputVmessWS() {
    raw="{
  \"v\":\"2\",
  \"ps\":\"\",
  \"add\":\"$IP\",
  \"port\":\"${port}\",
  \"id\":\"${uid}\",
  \"aid\":\"$alterid\",
  \"net\":\"${network}\",
  \"type\":\"none\",
  \"host\":\"${domain}\",
  \"path\":\"${wspath}\",
  \"tls\":\"tls\"
}"
    link=`echo -n ${raw} | base64 -w 0`
    link="vmess://${link}"

    echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
    echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
    echo -e "   ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
    echo -e "   ${BLUE}额外id(alterid)：${PLAIN} ${RED}${alterid}${PLAIN}"
    echo -e "   ${BLUE}加密方式(security)：${PLAIN} ${RED}none${PLAIN}"
    echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
    echo -e "   ${BLUE}伪装类型(type)：${PLAIN}${RED}none$PLAIN"
    echo -e "   ${BLUE}伪装域名/主机名(host)/SNI/peer名称：${PLAIN}${RED}${domain}${PLAIN}"
    echo -e "   ${BLUE}路径(path)：${PLAIN}${RED}${wspath}${PLAIN}"
    echo -e "   ${BLUE}底层安全传输(tls)：${PLAIN}${RED}TLS${PLAIN}"
    echo  
    echo -e "   ${BLUE}vmess链接:${PLAIN} $RED$link$PLAIN"
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

    echo -e "   ${BLUE}协议: ${PLAIN} ${RED}${protocol}${PLAIN}"
    if [[ "$trojan" = "true" ]]; then
        outputTrojan
        return 0
    fi
    if [[ "$vless" = "false" ]]; then
        if [[ "$kcp" = "true" ]]; then
            outputVmessKCP
            return 0
        fi
        if [[ "$tls" = "false" ]]; then
            outputVmess
        elif [[ "$ws" = "false" ]]; then
            outputVmessTLS
        else
            outputVmessWS
        fi
    else
        if [[ "$kcp" = "true" ]]; then
            link="vless://${uid}@${IP}:${port}?encryption=none&type=kcp&headerType=${Type}&seed=${seed}#${remark}"
            echo -e "   ${BLUE}VLESS+mKCP：${PLAIN}${RED}${link}${PLAIN}\n"
            echo -e "   ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
            echo -e "   ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
            echo -e "   ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
            echo -e "   ${BLUE}加密(encryption)：${PLAIN} ${RED}none${PLAIN}"
            echo -e "   ${BLUE}传输协议(network)：${PLAIN} ${RED}kcp${PLAIN}"
            echo -e "   ${BLUE}headerType：${PLAIN} ${RED}${Type}${PLAIN}"
            echo -e "   ${BLUE}mkcp seed：${PLAIN} ${RED}${seed}${PLAIN}" 
            echo -e "   ${BLUE}备注(remark)：${PLAIN} ${RED}${remark}${PLAIN}\n"

            echo -e "   ${BLUE}VLESS链接(link)：${PLAIN} ${RED}${link}${PLAIN}" 
        fi
        if [[ "$xtls" = "true" ]]; then
            link="vless://${uid}@${IP}:${port}?encryption=none&type=tcp&security=xtls&flow=${flow}&sni=${domain}#${remark}"
            echo -e "   ${BLUE}VLESS+XTLS：${PLAIN}${RED}${link}${PLAIN}\n"
            echo -e " ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
            echo -e " ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
            echo -e " ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
            echo -e " ${BLUE}流控(flow)：${PLAIN}$RED$flow${PLAIN}"
            echo -e " ${BLUE}加密(encryption)：${PLAIN} ${RED}none${PLAIN}"
            echo -e " ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
            echo -e " ${BLUE}伪装类型(type)：${PLAIN}${RED}none$PLAIN"
            echo -e " ${BLUE}伪装域名/主机名(host)/SNI/peer名称：${PLAIN}${RED}${domain}${PLAIN}"
            echo -e " ${BLUE}底层安全传输(tls)：${PLAIN}${RED}XTLS${PLAIN}"

            echo -e "   ${BLUE}VLESS链接(link)：${PLAIN} ${RED}${link}${PLAIN}" 
        elif [[ "$ws" = "false" ]]; then
            link="vless://${uid}@${IP}:${port}?encryption=none&type=tcp&security=tls&sni=${domain}#${remark}"
            echo -e "   ${BLUE}VLESS+TCP+TLS：${PLAIN}${RED}${link}${PLAIN}\n"
            echo -e " ${BLUE}IP(address):  ${PLAIN}${RED}${IP}${PLAIN}"
            echo -e " ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
            echo -e " ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
            echo -e " ${BLUE}流控(flow)：${PLAIN}$RED$flow${PLAIN}"
            echo -e " ${BLUE}加密(encryption)：${PLAIN} ${RED}none${PLAIN}"
            echo -e " ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
            echo -e " ${BLUE}伪装类型(type)：${PLAIN}${RED}none$PLAIN"
            echo -e " ${BLUE}伪装域名/主机名(host)/SNI/peer名称：${PLAIN}${RED}${domain}${PLAIN}"
            echo -e " ${BLUE}底层安全传输(tls)：${PLAIN}${RED}TLS${PLAIN}"

            echo -e "   ${BLUE}VLESS链接(link)：${PLAIN} ${RED}${link}${PLAIN}" 
        else
            link="vless://${uid}@${IP}:${port}?encryption=none&type=ws&security=tls&host=${domain}&path=${wspath}#${remark}"
            echo -e "   ${BLUE}VLESS+WS+TLS：${PLAIN}${RED}${link}${PLAIN}\n"
            echo -e " ${BLUE}IP(address): ${PLAIN} ${RED}${IP}${PLAIN}"
            echo -e " ${BLUE}端口(port)：${PLAIN}${RED}${port}${PLAIN}"
            echo -e " ${BLUE}id(uuid)：${PLAIN}${RED}${uid}${PLAIN}"
            echo -e " ${BLUE}流控(flow)：${PLAIN}$RED$flow${PLAIN}"
            echo -e " ${BLUE}加密(encryption)：${PLAIN} ${RED}none${PLAIN}"
            echo -e " ${BLUE}传输协议(network)：${PLAIN} ${RED}${network}${PLAIN}" 
            echo -e " ${BLUE}伪装类型(type)：${PLAIN}${RED}none$PLAIN"
            echo -e " ${BLUE}伪装域名/主机名(host)/SNI/peer名称：${PLAIN}${RED}${domain}${PLAIN}"
            echo -e " ${BLUE}路径(path)：${PLAIN}${RED}${wspath}${PLAIN}"
            echo -e " ${BLUE}底层安全传输(tls)：${PLAIN}${RED}TLS${PLAIN}"

            echo -e "   ${BLUE}VLESS链接(link)：${PLAIN} ${RED}${link}${PLAIN}"
        fi
    fi
}

showInfoWithSocks5() {
    showInfo
    # 检查是否存在 socks 协议
    socks_exists=$(jq -r '.inbounds[] | select(.protocol == "socks") | .protocol' $CONFIG_FILE)

    if [[ "$socks_exists" == "socks" ]]; then
        port=$(jq -r '.inbounds[] | select(.protocol == "socks") | .port' $CONFIG_FILE)
        listen=$(jq -r '.inbounds[] | select(.protocol == "socks") | .listen // "127.0.0.1"' $CONFIG_FILE)
        auth=$(jq -r '.inbounds[] | select(.protocol == "socks") | .settings.auth // "noauth"' $CONFIG_FILE)
        user=$(jq -r '.inbounds[] | select(.protocol == "socks") | .settings.accounts[0].user // empty' $CONFIG_FILE)
        pass=$(jq -r '.inbounds[] | select(.protocol == "socks") | .settings.accounts[0].pass // empty' $CONFIG_FILE)

        echo
        colorEcho $BLUE " SOCKS5配置信息："
        echo -e "   ${BLUE}监听地址: ${PLAIN}${RED}${IP}${PLAIN}"
        echo -e "   ${BLUE}监听端口: ${PLAIN}${RED}${port}${PLAIN}"
        if [[ "$auth" == "password" && -n "$user" && -n "$pass" ]]; then
            echo -e "   ${BLUE}认证方式: ${PLAIN}${RED}账号密码${PLAIN}"
            echo -e "   ${BLUE}用户名:   ${PLAIN}${RED}$user${PLAIN}"
            echo -e "   ${BLUE}密码:     ${PLAIN}${RED}$pass${PLAIN}"
            echo
            echo -e "   ${BLUE}用法：${PLAIN} ${RED}socks://${user}:${pass}@${IP}:${port}${PLAIN}"
        else
            echo -e "   ${BLUE}认证方式: ${PLAIN}${RED}无认证${PLAIN}"
            echo
            echo -e "   ${BLUE}用法：${PLAIN} ${RED}socks://${listen}:${port}${PLAIN}"
        fi
    fi
    # 生成二维码
    if command -v qrencode >/dev/null 2>&1; then
        echo
        echo "   [二维码如下，可用扫码工具/小火箭扫码导入]:"
        echo
        echo -n "$link" | qrencode -o - -t utf8
        echo
    else
        echo "(未检测到qrencode, 请安装: apt install -y qrencode)"
    fi
}

showQR() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi

    if [[ "$TROJAN" = "true" ]]; then
        echo -e "${GREEN} trojan链接：${PLAIN}"
        echo -e " trojan://${PASSWORD}@${DOMAIN}:${port}?security=tls&sni=${DOMAIN}#${DOMAIN}"
        echo ""
        echo -e " trojan二维码："
        echo -n " trojan://${PASSWORD}@${DOMAIN}:${port}?security=tls&sni=${DOMAIN}#${DOMAIN}" | qrencode -o - -t utf8
    elif [[ "$VLESS" = "false" ]]; then
        # VMESS
        echo -e "${GREEN} vmess链接：${PLAIN}"
        vmess="{\"add\":\"$DOMAIN\",\"aid\":\"$alterid\",\"host\":\"$DOMAIN\",\"id\":\"$uid\",\"net\":\"$network\",\"path\":\"$WSPATH\",\"port\":\"$port\",\"ps\":\"$DOMAIN\",\"scy\":\"auto\",\"sni\":\"$DOMAIN\",\"tls\":\"tls\",\"type\":\"none\",\"v\":\"2\"}"
        vmesslink=`echo -n $vmess | base64 -w 0`
        echo -e " vmess://${vmesslink}"
        echo ""
        echo -e " vmess二维码："
        echo -n " vmess://${vmesslink}" | qrencode -o - -t utf8
    else
        # VLESS
        echo -e "${GREEN} vless链接：${PLAIN}"
        if [[ "$XTLS" = "true" ]]; then
            echo -e " vless://${uid}@${DOMAIN}:${port}?security=xtls&flow=${FLOW}&sni=${DOMAIN}#${DOMAIN}"
            echo ""
            echo -e " vless二维码："
            echo -n " vless://${uid}@${DOMAIN}:${port}?security=xtls&flow=${FLOW}&sni=${DOMAIN}#${DOMAIN}" | qrencode -o - -t utf8
        else
            echo -e " vless://${uid}@${DOMAIN}:${port}?security=tls&sni=${DOMAIN}#${DOMAIN}"
            echo ""
            echo -e " vless二维码："
            echo -n " vless://${uid}@${DOMAIN}:${port}?security=tls&sni=${DOMAIN}#${DOMAIN}" | qrencode -o - -t utf8
        fi
    fi
}

showLog() {
    res=`status`
    if [[ $res -lt 2 ]]; then
        colorEcho $RED " Xray未安装，请先安装！"
        return
    fi

    journalctl -xen -u xray --no-pager
}

menu() {
    clear
    echo "#############################################################"
    echo -e "#                   ${RED}xray一键安装脚本${PLAIN}                         #"
    echo -e "# ${GREEN}作者${PLAIN}: 3000mall(CPLA_54J)                                  #"
    echo -e "# ${GREEN}网址${PLAIN}: https://3000mall.com                                #"
    echo -e "# ${GREEN}论坛${PLAIN}: https://bbs.3000mall.com                            #"
    echo -e "# ${GREEN}TG群${PLAIN}: https://t.me/3000mallclub                           #"
    echo -e "# ${RED}注意${PLAIN}: 本脚本仅内部，请不要外传，谢谢！                    #"
    echo -e "#                                                           #"	
    echo "#############################################################"
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
    echo -e "  ${GREEN}11.${PLAIN}  安装${BLUE}SOCKS5${PLAIN}${RED}(仅可与方案1/8共存)${PLAIN}"
    echo " -------------"
    echo -e "  ${GREEN}12.${PLAIN}  更新Xray"
    echo -e "  ${GREEN}13.  ${RED}卸载Xray${PLAIN}"
    echo " -------------"
    echo -e "  ${GREEN}14.${PLAIN}  启动Xray"
    echo -e "  ${GREEN}15.${PLAIN}  重启Xray"
    echo -e "  ${GREEN}16.${PLAIN}  停止Xray"
    echo " -------------"
    echo -e "  ${GREEN}17.${PLAIN}  查看Xray配置"
    echo -e "  ${GREEN}18.${PLAIN}  查看Xray日志"
    echo -e "  ${GREEN}19.${PLAIN}  查看当前配置二维码"
    echo " -------------"
    echo -e "  ${GREEN}0.${PLAIN}   退出"
    echo -n " 当前状态："
    statusText
    echo 

    read -p " 请选择操作[0-17]：" answer
    case $answer in
        0)
            exit 0
            ;;
        1)
            TLS="true"
            WS="true"
            install
            ;;
        2)
            KCP="true"
            install
            ;;
        3)
            TLS="true"
            install
            ;;
        4)
            install
            ;;
        5)
            VLESS="true"
            KCP="true"
            install
            ;;
        6)
            VLESS="true"
            TLS="true"
            install
            ;;
        7)
            VLESS="true"
            TLS="true"
            WS="true"
            install
            ;;
        8)
            VLESS="true"
            TLS="true"
            XTLS="true"
            install
            ;;
        9)
            TROJAN="true"
            TLS="true"
            install
            ;;
        10)
            TROJAN="true"
            TLS="true"
            XTLS="true"
            install
            ;;
        11)
            installSocks5CheckAndInstall
            ;;
        12)
            update
            ;;
        13)
            uninstall
            ;;
        14)
            start
            ;;
        15)
            restart
            ;;
        16)
            stop
            ;;
        17)
            showInfoWithSocks5
            ;;
        18)
            showLog
            ;;
        19)
            showQR
            ;;
        *)
            colorEcho $RED " 请选择正确的操作！"
            exit 1
            ;;
    esac
}

checkSystem

action=$1
[[ -z $1 ]] && action=menu
case "$action" in
    menu|update|uninstall|start|restart|stop|showInfo|showLog|showQR)
        ${action}
        ;;
    *)
        echo " 参数错误"
        echo " 用法: `basename $0` [menu|update|uninstall|start|restart|stop|showInfo|showLog]"
        ;;
esac
