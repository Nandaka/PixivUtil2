/**
 * @requires jquery.js
 * @requires prototype.js
 * @requires scriptaculous.js?load=effects
 * @requires rpc.js
 */

(function($) { // TMP


pixiv.embed = {
	url   : 'http://source.pixiv.net/source',
	input : null,
	select: null,

	setup: function() {
		var embed = pixiv.embed;
		if (!pixiv.context.embedId) return;
		embed.input = $('#embed-input'); //.focus(embed.focus);
		embed.select = $('#embed-select').change(embed.change).change();
	},

	focus: function(e) {
		setTimeout(function() {
			e.target.select();
		});
	},

	change: function(e) {
		var embed = pixiv.embed,
			context = pixiv.context,
			permalink, val, id, size, border, code;

		val = $(this).val().split('|');
		id = context.embedId;
		size = val[0];
		border = val[1];

		if (size == 'v1') {
			code = '<iframe src="http://embed.pixiv.net/code.php?id='+id+'" width="380" height="168" style="background:transparent" frameborder="0" marginwidth="0" marginheight="0" scrolling="no"></iframe>';
		}
		else {
			permalink = ('http://www.pixiv.net/member_illust.php?mode=medium&illust_id='+context.illustId).escapeTag();
			code = [
				'<script src="'+embed.url+'/embed.js" data-id="'+id+'" data-size="'+size+'" data-border="'+border+'" charset="utf-8"></script>',
				'<noscript>',
				'<p>',
				'<a href="'+permalink+'" target="_blank">'+permalink+'</a>',
				'</p>',
				'</noscript>'
			].join('');
		}
		embed.input.val(code);
		if (e.originalEvent)
			embed.input[0].focus();
	},

	showSample: function() {
		if (!$('#embed-sample').length) {
			$(pixiv.template('embed-sample', null, false)).appendTo('body');
			$LAB
				.script('/../embed.js?20110525')
				.wait(function() {
					__pixiv__.embed();
				});
		}
		pixiv.modal.open('#embed-sample', true);
	}
};


$(pixiv.embed.setup);


})(jQuery);



//======================================
//	Embedフォーム
//======================================
function embed_select(){
	embed_code.focus();
	embed_code.select();
}

//======================================
//	Embed Referer表示、非表示
//======================================
function embed_referer_view(){
	var btn  = $('embed_referer_view');
	var area = $('embed_referer_area');

	if(!area.visible()){
		new Effect.BlindDown("embed_referer_area", {
			duration:0.2
		});
		btn.innerHTML = '[ <a href="javascript:void(0);" onclick="embed_referer_view()">Embed Refererを閉じる</a> ]'
	}else{
		new Effect.BlindUp("embed_referer_area", {
			duration:0.2
		});
		btn.innerHTML = '[ <a href="javascript:void(0);" onclick="embed_referer_view()">Embed Referer表示</a> ]'
	}
}

//======================================
//コメント履歴表示、非表示
//======================================
function one_comment_view(){
	var btn_show = $('one_comment_view');
	var btn_hide = $('one_comment_view2');
	var area     = $('one_comment_area');

	if(area.empty()){
		// 表示(Ajaxで要素を取ってくる)
		var i_id = $('rpc_i_id').getAttribute('title');
		var u_id = $('rpc_u_id').getAttribute('title');

		var url  = './rpc_comment_history.php';
		var me   = 'post';
		var pars = 'i_id=' + i_id + '&u_id=' + u_id;
		var comp = on_loaded_one_comment_view;

		sendRequest(url, me, pars, comp);
		new Effect.BlindDown("one_comment_area", {
			duration:0.2
			});
		btn_show.hide();
		btn_hide.show();
	}else if(!area.visible()){
		new Effect.BlindDown("one_comment_area", {
			duration:0.2
		});
		btn_show.hide();
		btn_hide.show();
	}else{
		new Effect.BlindUp("one_comment_area", {
			duration:0.2
		});
		btn_show.show();
		btn_hide.hide();
	}
}

//======================================
//コメント履歴表示をクリック後
//======================================
function on_loaded_one_comment_view(oj){
    var obj = new showOneComment();
    obj.display(oj);
}

//======================================
//コメント履歴表示
//======================================
function showOneComment(){
    this.display = function(oj){
	var res = oj.responseText;
	var el  = $('one_comment_area');
	el.innerHTML = res;
    }
}

//======================================
// イラスト選択
//======================================
function select_illust(id) {
	var cbox = $('i_'+id); 
	var li   = $('li_'+id);
	
	if (cbox.checked == true) {
		li.className = 'display_works_edited';
	} else {
		li.className = '';
	}
}

function markAllUser( container_id ) {
	var rows = $(container_id).getElementsByTagName('li');
	var checkbox;

	for ( var i = 0; i < rows.length; i++ ) {
		checkbox = rows[i].getElementsByTagName( 'input' )[0];
		if(rows[i].getElementsByTagName( 'input' )[0] == null){ continue; }
		if ( checkbox && checkbox.type == 'checkbox' ) {
			if ( checkbox.checked == false ) {
				checkbox.checked = true;
				rows[i].className = 'display_works_edited';
			}
		}
	}
	return true;
}

function unmarkAllUser( container_id ) {
	var rows = $(container_id).getElementsByTagName('li');
	var checkbox;

	for ( var i = 0; i < rows.length; i++ ) {
		if(rows[i].getElementsByTagName( 'input' )[0] == null){ continue; }
		checkbox = rows[i].getElementsByTagName( 'input' )[0];
		if ( checkbox && checkbox.type == 'checkbox' ) {
			if ( checkbox.checked == true ) {
				checkbox.checked = false;
				rows[i].className = '';
			}
		}
	}
	return true;
}

//======================================
//キャプション表示、非表示
//======================================
function showHide(showTarget, hideTarget) {
  if( document.getElementById(showTarget)) {
          if( document.getElementById(showTarget).style.display == "none") {
              document.getElementById(hideTarget).style.display = "none";
              document.getElementById(showTarget).style.display = "block";
          } else {
              document.getElementById(showTarget).style.display = "none";
              document.getElementById(hideTarget).style.display = "block";
          } 
  }
}