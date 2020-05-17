var cp="";//当前章节
var np="";//下一章节
var number=0;//章节计数
var video=document.getElementsByTagName('video')[0];//视频对象
$('.exploreTip>div').html("广外的童鞋们请注意：<i style='color: #f00'>不要拖动进度条，不要自行操作</i>，一切都是自动的。如出现网络问题，请刷新页面再打开控制台执行一次");
if ($('.el-dialog__header>div>h4').text() == "弹题测验") {
		window.setTimeout(function () {
			$(".topic-list :first-child").click();
			$(".el-icon-close").click();
			$(".videoArea").click();
		}, 1000);
		setTimeout('drawWindow();',1000);
}else{
	setTimeout('drawWindow();',1000);
}


//绘制窗口
function drawWindow(){
//加载css文件
$('head').append('<link href="https://ghcdn.rawgit.org/LDS-Skeleton/OnlineCourseScript/master/main.css?t='+new Date().getTime()+'" rel="stylesheet" type="text/css" />');
//标签拼接
$("body").append("<div id='skdiv'></div>");
$("#skdiv").html("<p ><span style='font-weight:bold;    font-size: large;'>智慧树刷课脚本</span>（可用鼠标拖动）<p><p>版本：20200517 广西外国语学院市营专1906班</p><div id='content' style='   border-top: 2px solid;'></div>");
$('#content').html('<div ><p  id="rate_txt" >当前播放速度：默认1.25倍速</p><button id="startplay" onclick="start()">刷课任务加载成功，正在刷课..</button>');
$('#content').html($('#content').html()+"<div style='margin-top:10px'><p style='font-weight:bold'>当前进度:&nbsp;&nbsp;<span id='progress'>0%</span></p><hr></hr><p  id='cp'>当前章节：</p><p id='np'>下一章节：</p></div>");
dragPanelMove("#skdiv","#skdiv");
}


//鼠标拖动刷课框
function dragPanelMove(downDiv,moveDiv){
            $(downDiv).mousedown(function (e) {
                    var isMove = true;
                    var div_x = e.pageX - $(moveDiv).offset().left;
                    var div_y = e.pageY - $(moveDiv).offset().top;
                    $(document).mousemove(function (e) {
                        if (isMove) {
                            var obj = $(moveDiv);
                            obj.css({"left":e.pageX - div_x, "top":e.pageY - div_y});
                        }
                    }).mouseup(
                        function () {
                        isMove = false;
                    });
            });
}

//视频计数
for(var i=0;i<$('.video').length;i++){
	if($('.video').eq(i).find('b').length<3||$('.video').eq(i).find('svg').length!=0){
		number=i;
		break;
	}
}


//执行刷课
setTimeout(function () {
	$('.speedTab10').click();
	console.log("刷课任务加载成功，正在刷课...");
}, 3000);
setInterval(function () {
	cp=$('.video').eq(number).find('.catalogue_title').text();//当前章节
	np=$('.video').eq(number+1).find('.catalogue_title').text();//下一章节
	$('#cp').text("当前章节："+cp);
	$('#np').text("下一章节："+np);
	$('#progress').text($('.passTime').css('width'));
	//检测弹窗测试
	if ($('.el-dialog__header>div>h4').text() == "弹题测验") {
		window.setTimeout(function () {
			$(".topic-list :first-child").click();
			$(".el-icon-close").click();
			$(".videoArea").click();
		}, 1000);
	}
	//检测观看进度是否已达成
	if ($(".current_play div b:nth-child(2)").hasClass('time_icofinish') || $(".current_play div b:nth-child(3)").hasClass('time_icofinish')) {
		console.log("检测到视频观看完成，准备跳到下一节");
		//延时5秒执行操作
		setTimeout(function () {
			$('.nextButton').click()
			$(".videoArea").click();
		}, 5000);
		//视频加载完后，延时执行x1.25加速
		setTimeout(function () {
			$('.speedTab10').click();
		}, 5000);
		number++;
	}
}, 3000)
