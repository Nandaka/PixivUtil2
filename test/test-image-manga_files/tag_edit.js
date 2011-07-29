//======================================
//	タグ編集
//======================================
//======================================
//	タグ編集エリア呼び出し
//======================================
function startTagEdit(){
	var i_id = $('rpc_i_id').innerHTML;
	var u_id = $('rpc_u_id').innerHTML;
	var e_id = $('rpc_e_id').innerHTML;

	var url  = './rpc_tag_edit.php';
	var me   = 'post';
	var pars = 'mode=first&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id;
	var comp = on_loaded_tag;
	sendRequest(url, me, pars, comp);
}

//======================================
//	履歴呼び出し
//======================================
function startTagHistory(){

	var i_id = $('rpc_i_id').innerHTML;
	var u_id = $('rpc_u_id').innerHTML;
	var e_id = $('rpc_e_id').innerHTML;

	var url  = './rpc_tag_edit.php';
	var me   = 'post';
	var pars = 'mode=history&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id;
	var comp = on_loaded_history;
	sendRequest(url, me, pars, comp);
}

//======================================
//	タグ追加
//======================================
function addTag(){

	var i_id  = $('rpc_i_id').innerHTML;
	var u_id  = $('rpc_u_id').innerHTML;
	var e_id  = $('rpc_e_id').innerHTML;
	var value = $("add_tag").value;

	if(value != ''){
		$("add_tag_area").innerHTML = 'Loading ...';
		form_disabled();
		var url  = './rpc_tag_edit.php';
		var me   = 'post';
		var pars = 'mode=add_tag&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id+'&value='+encodeURIComponent(value);
		var comp = on_loaded_tag;
		sendRequest(url, me, pars, comp);
	}
}

//======================================
//	タグ削除
//======================================
function delTag(num, isMyself){

	var i_id  = $('rpc_i_id').innerHTML;
	var u_id  = $('rpc_u_id').innerHTML;
	var e_id  = $('rpc_e_id').innerHTML;
	var value = $("tag"+num).innerHTML;
	
	var t_node  = $('rpc_t_id');
	var t_id  = "";
	if(t_node){
		t_id = $('rpc_t_id').innerHTML;
	}

	if (value != ''){
		if (t_id == 'novel' || confirm("このタグを削除しますか？\n*投稿者にユーザーIDが通知されます。")) {
			$("del_btn_"+num).innerHTML = 'Loading ...';
			form_disabled();
			var url  = './rpc_tag_edit.php';
			var me   = 'post';
			var pars = 'mode=del_tag&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id+'&tag='+encodeURIComponent(value);
			var comp = on_loaded_tag;
			sendRequest(url, me, pars, comp);
		}
	}
}

//======================================
//	タグ復帰
//======================================
function getBackTag(num){

	var i_id  = $('rpc_i_id').innerHTML;
	var u_id  = $('rpc_u_id').innerHTML;
	var e_id  = $('rpc_e_id').innerHTML;
	var value = $("h_tag"+num).innerHTML;

	if(value != ''){
		$("getback_btn_"+num).innerHTML = 'Loading ...';
		form_disabled();
		var url  = './rpc_tag_edit.php';
		var me   = 'post';
		var pars = 'mode=add_tag&type=getback&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id+'&tag='+encodeURIComponent(value);
		var comp = on_loaded_tag;
		sendRequest(url, me, pars, comp);
	}
}

//======================================
//	タグ履歴削除
//======================================
function history_clear(){

	var i_id  = $('rpc_i_id').innerHTML;
	var u_id  = $('rpc_u_id').innerHTML;
	var e_id  = $('rpc_e_id').innerHTML;

	$("history_clear_btn").innerHTML = 'Loading ...';
	form_disabled();
	var url  = './rpc_tag_edit.php';
	var me   = 'post';
	var pars = 'mode=clear&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id;
	var comp = on_loaded_tag;
	sendRequest(url, me, pars, comp);
}

//======================================
//	タグロック
//======================================
function lockTag(num){

	var i_id  = $('rpc_i_id').innerHTML;
	var u_id  = $('rpc_u_id').innerHTML;
	var e_id  = $('rpc_e_id').innerHTML;
	var lock  = $("lock_tag"+num).checked;
	var value = $("tag"+num).innerHTML;

	if(lock == true){
		lock = 1;
	}else{
		lock = 0;
	}
	if(value != ''){
		var url  = './rpc_tag_edit.php';
		var me   = 'post';
		var pars = 'mode=lock_tag&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id+'&lock='+lock+'&tag='+encodeURIComponent(value);
		var comp = on_loaded_tag2;
		sendRequest(url, me, pars, comp);
	}
}

//======================================
//	タグを報告
//======================================
function infoTag(){

	var i_id   = $('rpc_i_id').innerHTML;
	var u_id   = $('rpc_u_id').innerHTML;
	var e_id   = $('rpc_e_id').innerHTML;
	var num    = $F('infotag');
	var value  = $("tag"+num).innerHTML;
	var result = $('info_tag_result');

	if(num == ''){
		result.style.display = 'block';
		result.innerHTML = '選択してください';
	}else{
		if(value != ''){
			result.style.display = 'block';
			result.innerHTML = 'Loading ...';
			form_disabled();

			var url  = './rpc_tag_edit.php';
			var me   = 'post';
			var pars = 'mode=info_tag&i_id='+i_id+'&u_id='+u_id+'&e_id='+e_id+'&num='+num+'&tag='+encodeURIComponent(value);
			var comp = on_loaded_tag3;
			sendRequest(url, me, pars, comp);
		}
	}
}

//======================================
//	メイン
//======================================
// タグ編集エリア表示
function on_loaded_tag(oj){
	var obj = new showTags();
	obj.display(oj);
}

function on_loaded_tag2(oj){
}

function on_loaded_tag3(oj){
	var obj = new showTags2();
	obj.display(oj);
}

function on_loaded_history(oj){
	var obj = new showHistory();
	obj.display(oj);
}


//======================================
//	タグ編集エリア表示
//======================================
function showTags(){
	// デコード
	this.decode = function(oj){
//		eval("var res = "+decodeURIComponent(oj.responseText));
		eval("var res = "+oj.responseText);
		return res;
	}

	// 表示
	this.display = function(oj){
		var res = this.decode(oj);

		// タグ変更エリア
		var data = '';
		for(var i=0; i<res.html.length; i++){
			data += res.html[i];
		}
		$("tag_edit").innerHTML = data;

		// 表示
		if(!$("tag_edit").visible()){
			ef1();
		}

		// 元の登録タグエリア
		if(res.mode == 'add_tag' || res.mode == 'del_tag'){
			data = '';
			for(i=0; i<res.tag_a.length; i++){
				data += res.tag_a[i];
			}
			$("tags").innerHTML = data;
		}
	}
}

//======================================
//	履歴表示
//======================================
function showHistory(){
	// デコード
	this.decode = function(oj){
//		eval("var res = "+decodeURIComponent(oj.responseText));
		eval("var res = "+oj.responseText);
		return res;
	}

	// 表示
	this.display = function(oj){
		var res = this.decode(oj);
		
		// タグ変更エリア
		var data = '';
		for(var i=0; i<res.html.length; i++){
			data += res.html[i];
		}
		$("tag_history").innerHTML = data;

		// 表示
		if(!$("tag_history").visible()){
			ef5();
		}
		$('tag_history_btn').innerHTML = '<a href="javascript:void(0);" onclick="endTagHistory('+res.i_id+','+res.u_id+','+res.e_id+')">閉じる</a>';
	}
}

//======================================
//	タグ編集エリア表示
//======================================
function showTags2(){
	// デコード
	this.decode = function(oj){
//		eval("var res = "+decodeURIComponent(oj.responseText));
		eval("var res = "+oj.responseText);
		return res;
	}

	// 表示
	this.display = function(oj){
		var res = this.decode(oj);
		$("info_tag_result").innerHTML = '報告しました';
		form_undisabled();
	}
}

//======================================
//	タグ編集終了
//======================================
function endTagEdit(){
	if($("tag_edit").visible()){
		ef3();
	}
}

//======================================
//	履歴終了
//======================================
function endTagHistory(i_id,u_id,e_id){
	if($("tag_history").visible()){
		ef6();
	}
	$('tag_history_btn').innerHTML = '<a href="javascript:void(0);" onclick="startTagHistory('+i_id+','+u_id+','+e_id+')">表示する</a>';
}

//======================================
//	エフェクト
//======================================
// effect
function ef1(){
	new Effect.BlindUp("tag_area", {
		delay:0.2,
		duration:0.2,
		afterFinish:ef2
	});
}

// effect2
function ef2(){
	new Effect.BlindDown("tag_edit", {
		delay:0.2,
		duration:0.5
	});
}

// effect3
function ef3(){
	new Effect.BlindUp("tag_edit", {
		delay:0.2,
		duration:0.5,
		afterFinish:ef4
	});
}

//effect4
function ef4(){
	new Effect.BlindDown("tag_area", {
		delay:0.2,
		duration:0.2
	});
}

// effect5
function ef5(){
	new Effect.BlindDown("tag_history", {
		delay:0.2,
		duration:0.5
	});
}

// effect6
function ef6(){
	new Effect.BlindUp("tag_history", {
		delay:0.2,
		duration:0.5
	});
}

//======================================
//	いろいろdisabled
//======================================
function form_disabled(){
	var rows = $('rpc').getElementsByTagName('tr');
	var res;
	var r;

	if($('add_tag_area').getElementsByTagName('input').length > 0){
		$('add_tag_area').getElementsByTagName('input')[0].disabled = true;
		$('add_tag_area').getElementsByTagName('input')[1].disabled = true;
	}
	if($('infoTagArea')!=null){
		if($('infoTagArea').getElementsByTagName('input')[0]!=null){
			$('infoTagArea').getElementsByTagName('input')[0].disabled = true;
		}
	}
	if($('info_tag_btn')!=null){
		if($('info_tag_btn').getElementsByTagName('input')[0]!=null){
			$('info_tag_btn').getElementsByTagName('input')[0].disabled = true;
		}
	}
	for ( var i = 0; i < rows.length; i++ ) {
		res = rows[i].getElementsByTagName( 'input' ).length;
		for( var j = 0; j < res; j++) {
			r = rows[i].getElementsByTagName( 'input' )[j]
			if ( r && (r.type == 'checkbox' || r.type == 'radio' || r.type == 'button' || r.type == 'submit') ) {
				r.disabled = true;
			}
		}
	}
	return true;
}

function form_undisabled(){
	var rows = $('rpc').getElementsByTagName('tr');
	var res;
	var r;

	if($('add_tag_area').getElementsByTagName('input').length > 0){
		$('add_tag_area').getElementsByTagName('input')[0].disabled = false;
		$('add_tag_area').getElementsByTagName('input')[1].disabled = false;
	}
	if($('info_tag_btn')!=null){
		if($('info_tag_btn').getElementsByTagName('input')[0]!=null){
			$('info_tag_btn').getElementsByTagName('input')[0].disabled = false;
		}
	}
	if($('history_clear_btn')!=null){
		if($('history_clear_btn').getElementsByTagName('input')[0]!=null){
			$('history_clear_btn').getElementsByTagName('input')[0].disabled = false;
		}
	}
	for ( var i = 0; i < rows.length; i++ ) {
		res = rows[i].getElementsByTagName( 'input' ).length;
		for( var j = 0; j < res; j++) {
			r = rows[i].getElementsByTagName( 'input' )[j]
			if ( r && (r.type == 'checkbox' || r.type == 'radio' || r.type == 'button' || r.type == 'submit') ) {
				r.disabled = false;
			}
		}
	}
	return true;
}