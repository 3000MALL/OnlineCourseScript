$( "#about_Dialog" ).on("click", function () {
  Helper.ui.dialog({
    title: "关于作者",
    content: "Hi,我是广西外国语学院市营专1906班的小伍同学！欢迎你使用本脚本！由于我平时工作比较忙，于是写出了这个脚本，方便自己的同时也方便忙碌的你。当然也请你妥善使用本脚本，如果你有时间了，好好看看这些课程，对自己也多多益善！如使用中有什么问题欢迎在微信提问，最后祝你学有所成，一切顺顺利利！------------------------市营专1906班 陈俊伍",
    darkMode: true
  });
})
$( "#dialog-9" ).on("click", function () {
  Helper.ui.dialog({
    title: "对话框标题",
    content: "对话框内容",
    autoClose: 5000
  });
})
