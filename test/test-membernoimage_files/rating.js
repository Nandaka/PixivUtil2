
(function($) { // TMP


$(function() {
	$('#rating').removeClass('loading'); // TMP
});


//======================================
//	評価されたら実効
//======================================
window.countup_rating = function(score) {
	var rtv = $("#jd_rtv").html();
	var rtc = $("#jd_rtc").html();
	var rtt = $("#jd_rtt").html();

	var e1 = $("#unit")[0];
	e1.innerHTML = 'Loading ...';
	var type_el = $('#rpc_t')[0];
	var type_dir = "";
	if (type_el != null && type_el.innerHTML != "") {
		type_dir = type + '/'; // type?
	}
	var i_id = $('#rpc_i_id').html();
	var u_id = $('#rpc_e_id').html();
	var qr   = $('#rpc_qr').html();
	var t_id = $('#rpc_t_id').html();

	var url  = './' + type_dir + 'rpc_rating.php';
	var me   = 'post';
	var pars = 'mode=save&i_id='+i_id+'&u_id='+u_id+'&qr='+qr+'&score='+score;
	var comp = function(){};

	sendRequest(url, me, pars, comp);

	var obj = new showSecond();
	var oj = {
		  'count' : (rtc - 0 + 1)
		, 'totalscore' : (rtt - 0 + score)
		, 'total_view' : (rtv == 0 ? 1 : rtv)
		, 'score' : score
		, 'rating_flg' : 0
		, 'put_score' : score
		, 're_sess' : true
		, 'qr' : qr
		, 't_id' : t_id
	};
	obj.display(oj);
};
window.send_rating = function(score) {
	var e1 = $("#unit")[0];
	e1.innerHTML = 'Loading ...';
	var type_el = $('#rpc_t')[0];
	var type_dir = "";
	if (type_el != null && type_el.innerHTML != "") {
		type_dir = type + '/'; // type?
	}
	var i_id = $('#rpc_i_id').html();
	var u_id = $('#rpc_e_id').html();
	var qr   = $('#rpc_qr').html();

	var url  = './' + type_dir + 'rpc_rating.php';
	var me   = 'post';
	var pars = 'mode=save&i_id='+i_id+'&u_id='+u_id+'&qr='+qr+'&score='+score;
	var comp = on_loaded_save;

	sendRequest(url, me, pars, comp);
};

//======================================
// 質の評価されたら実効
//======================================
window.send_quality_rating = function(num) {
	for(var i=0; i<5; i++){
		if($('#qr_kw'+(i+1)).length){
			$('#qr_kw'+(i+1))[0].disabled = true;
		}
	}
	var type_el = $('#rpc_t')[0];
	var type_dir = "";
	if (type_el != null && type_el.innerHTML != "") {
		type_dir = type + '/'; // type?
	}
	var i_id = $('#rpc_i_id').html();
	var u_id = $('#rpc_e_id').html();
	var qr   = $('#rpc_qr').html();
		
	var url  = './' + type_dir + 'rpc_rating.php';
	var me   = 'post';
	var pars = 'mode=save2&i_id='+i_id+'&u_id='+u_id+'&qr='+qr+'&num='+num;
	var comp = on_loaded_save2;

	sendRequest(url, me, pars, comp);
}

//======================================
//	メイン
//======================================
// 評価後
function on_loaded_save(oj){
	var obj = new showSecond();
	obj.display(oj);
}

function on_loaded_save2(oj){
	var obj = new showSecond2();
	obj.display(oj);
}

//======================================
//	評価後
//======================================
function showSecond(){
	// デコード
	this.decode = function(oj){
		eval("var res = "+decodeURIComponent(oj.responseText));
		return res;
	}

	// 表示
	this.display = function(res){
		// var res = this.decode(oj);

		var qr = res.qr;
		var el = $('#unit')[0];
		var t_id = res.t_id;

		var width = res.score*26;
		var data = "";
		data += "<h4>";
		data += "閲覧数："+res.total_view+"　評価回数："+res.count+"　総合点："+res.totalscore;
		if(qr == 1){
			if (t_id && t_id == 'novel') {
				data += '　<a href="questionnaire.php"><img src="http://source.pixiv.net/source/images/icon_questionnaire.gif" alt="作品アンケート有り" /></a>';
			} else {
				data += '　<a href="questionnaire_illust.php"><img src="http://source.pixiv.net/source/images/icon_questionnaire.gif" alt="作品アンケート有り" /></a>';
			}
		}
		data += "</h4>\n";
		data += "<ul class='unit-rating'>\n";
		data += "<li class='current-rating' style='width:"+width+"px;'></li>\n";
		for(var i=1; i<=10; i++){
			data += "<li class='r"+i+"-unit'></li>\n";
		}
		data += "</ul></div>\n";
		if(res.rating_flg==1){
			data += "<h4>あなたの評価 "+res.put_score+"（評価できるのは1日1回です）\n</h4>";
		}else{
			data += "</div><h4>評価を受け付けました！"+res.score+"点\n</h4>";
		}
		el.innerHTML = data
	}
}

//======================================
// 質の評価後
//======================================
function showSecond2() {
	// デコード
	this.decode = function(oj){
		eval("var res = "+decodeURIComponent(oj.responseText));
		return res;
	}
	
	// 表示
	this.display = function(res) {
		// var res = this.decode(oj);

		var value = res.keyword;
		var html  = res.html;
		
		if(!$('after_q_rating')){
			// 通常
			var data  = $('#rating').html();
			$('#rating').html(data+'<h4><a href="javascript:void(0);" onclick="onOff(\'result\');">作品アンケート：'+value+'</a></h4>>'+html);
		}else{
			// 評価をしたあと作品アンケートをしないでリロードしたあとなどに実行した場合
			$('#after_q_rating').remove();
			var data  = $('#rating').html();
			$('#rating').html(data+'<h4><a href="javascript:void(0);" onclick="onOff(\'result\');">作品アンケート：'+value+'</a></h4>'+html);
		}
		if(!$('#rating').is(':visible')) {
			rating_ef2();
		}
	}
}

//======================================
// 結果表示
//======================================
window.onOff = function(id) {
	var el = $('#' + id);
	el.toggle();
};

//======================================
// エフェクト
//======================================
window.rating_ef = function() {
	$('#quality_rating').slideDown('fast');
};

window.rating_ef2 = function() {
	$('#quality_rating').slideUp('fast', rating_ef3);
};

window.rating_ef3 = function() {
	$('#rating').slideDown('fast');
};

window.rating_ef4 = function() {
	$('#rating').slideUp('fast', rating_ef);
};


function sendRequest(url, method, params, callback) {
	$.ajax({
		url     : url,
		type    : method,
		data    : params,
		dataType: 'json',
		success : callback
	});
}


})(jQuery);
