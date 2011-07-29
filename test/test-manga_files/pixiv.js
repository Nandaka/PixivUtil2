/**
 * @requires LAB.js
 * @requires jquery.js
 * @requires lib.js
 */

// TODO remove. use $.proxy
// https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Function/bind
if (!Function.prototype.bind) Function.prototype.bind = function(obj) {
	var slice = [].slice,
		args = slice.call(arguments, 1),
		self = this,
		nop = function() {},
		bound = function() {
			return self.apply(
				this instanceof nop ? this : (obj || {}),
				args.concat(slice.call(arguments))
			);
		};
	nop.prototype = self.prototype;
	bound.prototype = new nop();
	return bound;
};


// use pixiv.escapeHTML
String.prototype.escapeTag = function() {
	return this.toString()
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');
};

Number.prototype.escapeTag = function() {
	return this.toString().escapeTag();
};

Number.prototype.unescapeTag = function() {
	return this.toString().unescapeTag();
};

String.prototype.unescapeTag = function() {
	return this.toString()
		.replace(/&amp;/g, '&')
		.replace(/&quot;/g, '"')
		// .replace(/&#039;/g, "'")
		.replace(/&lt;/g, '<')
		.replace(/&gt;/g, '>');
};


(function(w, d, $) {


var pixiv = w.pixiv = $.extend({
	platform: null,
	user    : {},
	context : {},
	text    : {},
	config  : {
		pTlAPIKey: '18c61f5d457c2c15d866a8bf4f5a414b1d277b93'
	}
}, w.pixiv);

$.fx.interval = 50;

$.support.placeholder = 'placeholder' in d.createElement('input');
$.support.console = !!(w.console && w.console.log);
$.support.storage = !!(w.sessionStorage && w.localStorage);
$.support.json = !!w.JSON;

$.browser.msie7 = $.browser.msie && $.browser.version < 8;
$.browser.msie8 = $.browser.msie && $.browser.version < 9;
$.browser.touchDevice = $.browser.touchDevice || pixiv.platform == 'touch' || (/iP(?:hone|ad|od)/.test(navigator.platform));

// $.tmpl && ($.tmpl.tag['script'] = {
// 	open : "if('$2'){__.push('<sc'+'ript $2></sc'+'ript>'));}else{__.push('<sc'+'ript>');}",
// 	close: "__.push('</sc'+'ript>');"
// });

$.fn.searchForm = function() {
	var z_index = 1000;
	var prefix = pixiv.dispatcher.match(/^\/novel\//, location.pathname) ? '/novel' : '';
	return this.each(function() {
		var form = this;
		var bookmark = $(this)
			.css('z-index', z_index--) // TMP
			.hasClass('bookmark');
		var text = $('input.text', this);
		var input = text[0];
		var s_mode = $('input[name="s_mode"]', this);
		var supported_placeholder = $.support.placeholder;
		var placeholder;
		if (!supported_placeholder) {
			placeholder = $('div.placeholder', this).click(function() {
				$(this).hide();
				input.focus();
			});
			text
				.blur(function() {
					if (!text.val()) placeholder.show();
				})
				.blur();
		}

		var menu = $('ul.menu', this);
		var menu_button = $('div.menu-button', this).hover(
			function() { menu.show(); },
			function() { menu.hide(); }
		);
		$('li:not(.random-pickup)', menu).click(function() {
			var li = $(this);
			var klass = this.className;
			var type = li.text();
			if (supported_placeholder)
				text.attr('placeholder', type);
			else
				placeholder.hide().text(type);

			s_mode.val(klass);
			if (!bookmark)
				switch (klass) {
					case 's_web':
						form.action = '/search.php';
						input.name = 'keywords';
						break;
					case 's_usr':
						form.action = '/search_user.php';
						input.name = 'nick';
						break;
					default:
						form.action = prefix+'/search.php';
						input.name = 'word';
				}
			menu_button.mouseleave();
			input.focus();
		});
	});
};

$.fn.placeholder = function() {
	var supported = $.support.placeholder;
	if (!supported) {
		this.each(function() {
			var input = $('input[placeholder]', this);
			if (input.length) {
				var placeholder = $('<div class="placeholder">' + input.attr('placeholder') + '</div>')
					.insertBefore(input)
					.click(function() {
						placeholder.hide();
						input.focus();
					});
				input
					.blur(function() {
						if (!input.val()) {
							placeholder.show();
						}
					})
					.blur();
			}
		});
	}
};

$.fn.selectbox = function(options) {
	options = options || {};

	return this.each(function() {
		// TODO create on-demand
		var self = $(this);
		var current = options.current || $('div.current', this);
		var item_container = options.item_container || $('ul.items', this);
		var items = $('li', item_container);
		var current_item = options.default_item || items.filter('.current');
		var callback = options.callback;

		var initialize = false;
		self.hover(
			function() {
				if (!initialize) {
					items.each(function() {
						var item = $(this).click(function(e) {
							if (item.hasClass('current')) return false;
							current_item.removeClass('current');
							current_item = item.addClass('current');
							current.text(current_item.text());
							self.mouseleave();
							if (callback)
								return callback.call(this, e);
						});
					});
					initialize = true;
				}
				item_container.show();
			},
			function() { item_container.hide(); }
		);
	});
};


$.fn.urlLink = $.fn.urlAutoLink = function() {
	return this.each(function() {
		this.innerHTML = pixiv.addURLLink(this.innerHTML);
	});
};

$.fn.hashTagLink = $.fn.hashTagAutoLink = function() {
	return this.each(function() {
		this.innerHTML = pixiv.addHashTagLink(this.innerHTML);
	});
};


// countStrlen.js
/**
 * 入力文字数カウント
 * 
 * @param input_id  入力エリアID
 * @param output_id 出力エリアID
 * @param maxlen    最大文字数
 */
window.countStrlen = function(input_id, output_id, maxlen) {
	if (input_id == '' || output_id == '' || maxlen == '') {
		return false;
	}
	
	var count = $('#'+input_id).val().replace(/\r\n?/, "\n").length;
	
	if (maxlen < count) {
		$('#'+output_id).html('<span class="error">'+ count +'</span>');
	} else {
		$('#'+output_id).html(count);
	}
};

/**
 * タグカウント
 * 
 * @param input_id  入力エリアID
 * @param output_id 出力エリアID
 * @param maxtag    最大タグ数
 */
window.countTags = function(input_id, output_id, maxtags) {
	if (input_id == '' || output_id == '' || maxtags == '') {
		return false;
	}

	var value   = $.trim($('#'+input_id).val());
	var count_a = value.split(/\s+|　+/);
	if (count_a == '') {
		return false;
	}

	var tag_count = count_a.length;
	$('#'+output_id).html(tag_count > maxtags ? '<span class="error">'+tag_count+'</span>' : tag_count);
	// if (maxtags < length) {
	// 	$('#'+output_id).html('<span class="error">'+count_a.length+'</span>';
	// } else {
	// 	$('#'+output_id).innerHTML = count_a.length;
	// }
};


$.extend(pixiv, {
	setup: function() {
		$(pixiv.setupReady);
		w.onload = pixiv.setupLoad;

		// TODO move to initialize.js 別ファイルに分けてpixiv.jsのキャッシュを効きやすくする
		var module = pixiv.pageModule, page = pixiv.page;
		pixiv.dispatcher
			.connect(/^\/(?:content_upload_fix|event_detail|member_illust(?:_.+)?|bookmark_add|ranking|ranking_log|novel\/bookmark_add|novel\/show|info|user_event(?:_.+)?)\.php$/, module.tweetButton).and()
			.connect(/^\/user_event(?:_.+)?\.php$/, module.twitterWidget).and()
			.connect(/^\/member_illust\.php$/, page['member_illust'])
			.connect({ pathname: /^\/bookmark\.php$/, search: /type=user\W?/ }, page['bookmark?type=user'])
			// .connect(/^\/stacc\/$/,  page.stacc) // ベータのコミケマップ用だったのでコメントアウト
			.connect(/^\/novel\/show\.php$/, page['novel/show'])
			.connect(/^\/setting_design\.php$/, page['setting_design'])
			// .connect(/^\/tags\.php$/, pixiv.page.tags)
			// .connect(/^\/search\.php$/, pixiv.page.search)
			.connect(/^\/ranking\.php$/, page.ranking)
			.connect(/^\/ranking_log\.php$/, page.rankingLog)
			.connect(/^\/event_member\.php$/, page.eventMember)
			.connect({pathname: /^\/search_user\.php$/, search: ''}, page['search_user'])
			.dispatch();
	},

    setupReady: function() {
		pixiv.body = $('body');
		$.browser.touchDevice && pixiv.body.addClass('is-touch-device');

		$('form.search').searchForm();
        // $('form').placeholder();
		// TMP
		$('form.ui-search').each(function() {
			var self = $(this),
				input = $('input[type="text"]', this),
				clear = $('div.clear', this);

			input
				.keyup(function() {
					input.val() ? self.addClass('has-text') : self.removeClass('has-text');
				})
				.keyup();
			clear.click(function() {
				input.val('').keyup()[0].focus();
			});
		});

		$('.selectbox').selectbox();
		$('.page-top').click(pixiv.scroll);

		pixiv.ad.setup();
		pixiv.modal.setup();
		// TODO 整理
		pixiv.popupManager.setup();
		pixiv.screen.setup();
		pixiv.dialog.setup();

		if (pixiv.context.userId) {
			new pixiv.Favorite().initialize();
			new pixiv.MyPixiv().initialize();
		}
		pixiv.Popup.setup();

		pixiv.scrollView.setup();
		// pixiv.ui.lazyImage.setup();


		pixiv.ui.selectBox.setup();
		pixiv.ui.tooltip.setup();
	    
		pixiv.suggest.setup();

		pixiv.EventTracker.setup();

		if (pixiv.context.userRecommendSampleUser && $('#user-recommend-container').length) {
			pixiv.userRecommendMenu.load();
		}

		if (pixiv.context.showCircleList) {
			pixiv.dispatcher.connect(/^\/(?:tags|search)\.php$/, pixiv.pageModule.circleList).and();
		}
		pixiv.dispatcher.dispatch();
	},

	setupLoad: function() {
		pixiv.ui.shareButton.setup();

		pixiv.dispatcher
			.connect('/', function() {
				pixiv.widget.facebookLikeBox('#facebook-like-box');
				pixiv.widget.twitterWidget();
			})
			.dispatch();

		// AutoPagerize
		try {
			document.body.addEventListener('AutoPagerize_DOMNodeInserted', function(e) {
				pixiv.scrollView.add('.ui-scroll-view', e.target);
			});
		}
		catch (e) {}
	},

	log         : log,
	escapeHTML  : escapeHTML,
	unescapeHTML: unescapeHTML,
	throttle    : throttle,
	debounce    : debounce	
});

!$.support.console && (w.console = {log: pixiv.log});

pixiv.window = $(w);
pixiv.document = $(d);

pixiv.development = w.location.hostname != 'www.pixiv.net';
pixiv.sourcePath = pixiv.development ? '/source' : 'http://source.pixiv.net/source';

$LAB.setGlobalDefaults({BasePath: pixiv.sourcePath + '/js'}); // TODO move

function log() {
	if (!pixiv.development) return;

	var args = $.makeArray(arguments);
	if (!args.length) return;

	if ($.support.console && !$.browser.touchDevice) {
		'apply' in console.log ?
			console.log.apply(console, args) :
			console.dir ?
				console.dir(args) :
				console.log(args);
	}
	else {
		$('<div class="console">' + args.join(', ') + '</div>').appendTo('body');
	}
}

function escapeHTML(str) {
	return str.toString()
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');
}

function unescapeHTML(str) {
	return str.toString()
		.replace(/&amp;/g, '&')
		.replace(/&quot;/g, '"')
		// .replace(/&#039;/g, "'")
		.replace(/&lt;/g, '<')
		.replace(/&gt;/g, '>');
}

function throttle(method, context, wait) {
	!wait && (wait = 500);
	var timer = null;

	return function() {
		if (timer) return;
		var args = arguments;

		method.apply(context, args);

		timer = setTimeout(function() {
			timer = null;
			method.apply(context, args);
		}, wait);
	};
}

function debounce(method, context, wait) {
	!wait && (wait = 500);
	var timer = null;

	return function() {
		timer && clearTimeout(timer);

		var args = arguments;

		timer = setTimeout(function() {
			timer = null;
			method.apply(context, args);
		}, wait);
	};
}


pixiv.dispatcher = {
	location: window.location,
	stash   : [],

	connect: function(paths, action) {
		if (paths || paths === 0) {
			paths = paths.valueOf();
			if (!(typeof paths == 'object' && !(paths instanceof RegExp))) // webkit: typeof RegExp == 'function'
				paths = {pathname: paths};
			pixiv.dispatcher.stash.push([paths, action]);
		}
		return pixiv.dispatcher;
	},

	and: function() {
		var stash = pixiv.dispatcher.stash,
			length = stash.length;
		length && (stash[length - 1][2] = true);
		return pixiv.dispatcher;
	},

	dispatch: function(location) {
		var dispatcher = pixiv.dispatcher;
		location = location || dispatcher.location;
		var stash = dispatcher.stash,
			params = {};
		for (var i = 0, c; c = stash[i]; ++i) {
			var paths = c[0], action = c[1], chain = c[2];
			var matched = false;
			for (var k in paths) {
				var v = paths[k];
				var path = location[k];
				if (!path) continue;
				var m = dispatcher.match(v, path);
				matched = !!m;
				if (matched)
					params[k] = m;
				else
					break;
			}
			if (matched) {
				action && action(params);
				if (!chain) {
					break;
				}
			}
		}
		dispatcher.clear();
		return dispatcher;
	},

	match: function(value, path) {
		var ret;
		if (value instanceof RegExp)
			ret = value.exec(path) || false;
		else {
			value = value.toString();
			ret = (path.indexOf(value) != -1) && value;
		}
		return ret;
	},

	clear: function() {
		pixiv.dispatcher.stash = [];
		return pixiv.dispatcher;
	}
};


$.extend(pixiv, {
	template   : template,
	queryString: queryString,
	iframe     : iframe
});

pixiv.template.replace = templateReplace;

var template_markup = /\{= ([^}]+)\}/g;

function template(selector, params, escape) {
	template = $('#template-' + selector).html();
	return pixiv.template.replace(template, params, escape);
}

function templateReplace(template, params, escape) {
	return !template || !params ?
		template :
		template.replace(template_markup, function(_, p) {
			p = params[p] || '';
			return escape === false ? p : pixiv.escapeHTML(p);
		});
}

function queryString(queries, escape) {
	var ret = [], k, v;
	for (k in queries) {
		v = queries[k];
		v === null && (v = ''); 
		v !== undefined && ret.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
	}
	ret = ret.join('&');
	return escape ? pixiv.escapeHTML(ret) : ret;
}

function iframe(path, q) {
	return '<iframe src="' + path + '?' + pixiv.queryString(q, true) + '" frameborder="0" allowtransparency="true" scrolling="no"></iframe>';
}


pixiv.suggest = {
	container     : null,
	inputContainer: null,
	listContainer : null,
	listItem      : null,
	keyword       : null,
	_keyword      : null,
	stash         : {},
	listPosition  : -1,
	listLength    : 0,
	effectiveCount: 5,
	setup         : suggestSetup,
	handleEvent   : suggestHandleEvent,
	select        : suggestSelect,
	submit        : suggestSubmit,
	click         : suggestClick,
	start         : suggestStart,
	stop          : suggestStop,
	request       : suggestRequest,
	filter        : suggestFilter,
	show          : suggestShow,
	hide          : suggestHide
};

function suggestSetup() {
	if (!pixiv.user.premium) return;

	this.container = $('#suggest-container');
	if (!this.container.length) return;
	this.inputContainer = $('#suggest-input');
	this.listContainer = $('#suggest-list');

	if ($.browser.msie8) {
		this.inputContainer
			.focus($.proxy(this.start, this))
			.blur($.proxy(this.stop, this))
			.keydown($.proxy(this.select, this));
		this.container.submit($.proxy(this.submit, this));
		this.listContainer.click($.proxy(this.click, this));
	}
	else { // faster
		var input = this.inputContainer[0];
		input.addEventListener('focus', this, false);
		input.addEventListener('blur', this, false);
		input.addEventListener('keydown', this, false);
		this.container[0].addEventListener('submit', this, false);
		this.listContainer[0].addEventListener('click', this, false);
	}
}

function suggestHandleEvent(e) {
	switch (e.type) {
	case 'focus':
		this.start(e);
		break;

	case 'blur':
		this.stop(e);
		break;

	case 'keydown':
		this.select(e);
		break;

	case 'submit':
		this.submit(e);
		break;

	case 'click':
		this.click(e);
		break;
	}
}

function suggestSelect(e) {
	var which = e.which,
		position = this.listPosition;

	switch (which) {
	case 38: // ↑
	case 40: // ↓
		if (e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) break;

		e.preventDefault();
		if (this.listItem) {
			var length = this.listLength;
			position = this.listPosition = which == 38 ?
				(position - 1 >= -1 ? position - 1 : length - 1) :
				(position + 1 < length ? position + 1 : -1);

			this.listItem.removeClass('current');
			position != -1 && this.listItem.eq(position).addClass('current');
		}
		break;

	case 13: // return
		if (this.listItem && position != -1) {
			e.preventDefault();
			this.click({target: this.listItem[position]});
		}
		break;
	}
}

function suggestSubmit(e) {
	this.inputContainer.val($.trim(this.inputContainer.val()));
}

function suggestClick(e) {
	if (e.target) {
		var container = this.inputContainer,
			text = container.val().split(/\s+/);
		text[text.length - 1] = $(e.target).text();

		container.val(text.join(' '))[0].focus();
		this.hide();
	}
}

function suggestStart() {
	this.stop();
	this.timer = setInterval($.proxy(this.request, this), 500);
	// this.request();
}

function suggestStop() {
	clearInterval(this.timer);
	setTimeout($.proxy(this.hide, this), 100); // TMP
}

function suggestRequest() {
	var self = this,
		keyword = $.trim(this.inputContainer.val().split(/\s+/).pop()),
		effective_keyword,
		data,
		dry;

	if (!keyword) {
		this.hide();
		return;
	}
	if (keyword == this.keyword || keyword == this._keyword) return;

	if (keyword.length > this.effectiveCount) {
		effective_keyword = keyword.slice(0, this.effectiveCount);
		data = this.stash[effective_keyword];
		if (data) {
			data = this.stash[keyword] || this.filter(data, keyword);
			if (data) {
				this._keyword = keyword;
				this.stash[keyword] = data;
				this.show(data);
			}
			return;
		}
		else {
			keyword = effective_keyword;
			dry = true;
		}
	}
	else {
		data = this.stash[keyword];
		this._keyword = null; // 6文字以上から5文字に削られた場合に沈黙しないように
	}
	this.keyword = keyword;
	if (data) {
		this.show(data);
	}
	else {
		this.stash[keyword] = {};
		pixiv.api.suggest(keyword).done(function(data) {
			self.stash[keyword] = data;
			!dry && self.show(data);
		});
	}
}

function suggestFilter(data, keyword) {
	var ret = [];
	for (var i = 0, items = data.candidates, item; item = items[i]; ++i) {
		if (item.tag_name.indexOf(keyword) === 0) {
			ret.push(item);
		}
	}
	return {candidates: ret};
}

function suggestShow(data) {
	var items = (data || {}).candidates,
		length = items.length,
		li = [];
	if (length) {
		this.listLength = length;
		for (var i = 0, item; item = items[i]; ++i) {
			li[i] = '<li>' + item.tag_name + '</li>';
		}
		this.listItem = $(li.join('')).appendTo(
			this.listContainer.empty().show()
		);
		this.listPosition = -1;
	}
	else {
		this.hide();
	}
}

function suggestHide() {
	this.listContainer.hide();
	this.listPosition = -1;
	this.keyword = null;
	this._keyword = null;
}


pixiv.shortcut = {
	keys       : {},
	initialized: false,

	setup: function() {
		var self = this;
		$($.browser.msie ? document : window).keypress(function(e) {
			if (/^(?:input|textarea)$/.test(e.target.tagName.toLowerCase())) {
				return;
			}
			var handler = self.keys[e.which] || self.keys[String.fromCharCode(e.which)];
			if (handler) {
				handler();
			}
		});
		this.initialized = true;
	},

	bind: function(key, handler) {
		this.initialized || this.setup();
		this.keys[key] = handler;
		return this;
	},

	unbind: function(key) {
		delete this.keys[key];
		return this;
	},

	trigger: function(key) {
		this.keys[key]();
	}
};


pixiv.widget = {
	facebookLikeBox: widgetFacebookLikeBox,
	twitterWidget  : widgetTwitterWidget,
	openTwitter    : widgetOpenTwitter,
	openMixiCheck  : widgetOpenMixiCheck
};

function widgetFacebookLikeBox(target) {
	$(pixiv.iframe('http://www.facebook.com/plugins/likebox.php', $(target).data())).appendTo(target);
}

function widgetTwitterWidget() {
	var options = pixiv.context.twitterWidgetOptions;
	options && $LAB
		.script('http://widgets.twimg.com/j/2/widget.js')
		.wait(function() {
			new TWTR.Widget(options).render().start();
		});
}

function widgetOpenTwitter(url) {
	w.open(url, 'twitter', 'width=550,height=450,personalbar=0,toolbar=0,scrollbars=1,resizable=1');
	return false;
}

function widgetOpenMixiCheck(url) {
	w.open(url, 'mixi_check', 'width=632,height=456,location=yes,resizable=yes,toolbar=no,menubar=no,scrollbars=no,status=no');
	return false;
}


pixiv.userRecommendMenu = {
	load: userRecommendMenuLoad
};

function userRecommendMenuLoad() {
	pixiv.api.recommender.user(pixiv.context.userRecommendSampleUser)
		.done(userRecommendMenuShow);
}

function userRecommendMenuShow(data) {
	data = data.recommend_users;
	if (data && data.length) {
		var ul = $('#user-recommend-container')
			.show()
			.find('ul.users');
		$('#template-user-recommend-list').tmpl(data).appendTo(ul);
	}
}


pixiv.userRecommend = {
	stash         : null,
	container     : null,
	usersContainer: null,
	template      : null,
	offset        : 0,
	setup         : userRecommendSetup,
	load          : userRecommendLoad,
	show          : userRecommendShow,
	hideUser      : userRecommendHideUser 
};

function userRecommendSetup() {
	this.container = $('#search-result');
	this.usersContainer = $('ul.users', this.container);
	this.template = $('#template-user-recommend');
	this.load();
}

function userRecommendLoad() {
	var self = this,
		container = this.container;
	container.addClass('loading-chobi');
	pixiv.api.recommender.user(pixiv.context.userRecommendSampleUser, 100, true)
		.done(function(data) {
			self.container.removeClass('loading-chobi');
			if (data.error) {
				var no_item = $('div.no-item', container);
				no_item
					.text(e)
					.show();
			}
			else {
				self.stash = data.recommend_users;
				self.show();
			}
		});
		// .fail(function(e) {
		// 	var no_item = $('div.no-item', container);
		// 	e && no_item.text(e);
		// 	no_item.show();
		// });
}

function userRecommendShow() {
	var users = this.stash.splice(0, 20);
	if (users.length) {
		if (!this.offset) {
			if (this.stash.length) {
				$('div.more', this.ontainer).show();
			}
		}
		if (!this.stash.length) {
			$('div.more', this.container).remove();
		}

		this.template.tmpl(users).appendTo(this.usersContainer);
		this.offset += users.length;
	}
	else if (!this.offset) {
		throw null;
	}
}

function userRecommendHideUser(id) {
	pixiv.api.recommender.hideUser(id);

	pixiv.ui.tooltip.container.hide();

	var container = $('#user-' + id).animate({
		width  : 0,
		opacity: 0
	}, 350, function() {
		container.remove();
	});
}


pixiv.modal = {
	container          : null,
	backgroundContainer: null,
	setup              : modalSetup,
	add                : modalAdd,
	addBackground      : modalAddBackground, // ex. ad
	hide               : modalHide,
	showBackground     : modalShowBackground,
	click              : modalClick,
	open               : modalOpen,
	close              : modalClose
};

function modalSetup() {
	pixiv.body.live('click.modal', $.proxy(this.click, this));
}

function modalAdd(container) {
	this.container = this.container ?
		this.container.add(container) :
		$(container);
}

function modalAddBackground(container) {
	this.backgroundContainer = this.backgroundContainer ?
		this.backgroundContainer.add(container) :
		$(container);
}

function modalHide() {
	if (this.container) {
		this.container.hide();
		this.container = null;
	}
}

function modalShowBackground() {
	this.backgroundContainer && this.backgroundContainer.show();
}

function modalClick(e) {
	var target = $(e.target);
	if (!target.hasClass('ui-modal-trigger') && !target.closest(this.container).length) {
		this.hide();
		this.showBackground();
	}
}

function modalOpen(container, blocking) {
	container = $(container);
	this.close();
	this.add(container);

	if (blocking) {
		this.backgroundContainer && this.backgroundContainer.hide();
		container.css('top', pixiv.window.scrollTop());
	}
	container.show();
	return container;
}

function modalClose() {
	this.hide();
	this.showBackground();
}


pixiv.ui = {
	loadContextShareButton: uiLoadContextShareButton,
	openModal             : uiOpenModal, // TODO remove
	closeModal            : uiCloseModal // TODO remove
};

function uiLoadContextShareButton(e, data) { // TODO replace的なメソッドがあればいい？
	$('#template-ui-context-share-button')
		.tmpl(data)
		.appendTo(this)
		.filter('.share-button-twitter').each(pixiv.ui.shareButton.twitter).end() // TODO 最適化出来そう
		.filter('.share-button-facebook').each(pixiv.ui.shareButton.facebook);
}


function uiOpenModal(id) { // TODO 高さをウィンドウに合わせるオプション
	$('#' + id)
		.show()
		.css('padding-top', pixiv.window.scrollTop());

	$('#pageAdver, .adver_footer').hide(); // TODO pixiv.ad に移す
}


function uiCloseModal() {
	$('.group-modal').hide();
	$('#pageAdver, .adver_footer').show(); // TODO pixiv.ad に移す
}


pixiv.scrollView = {
	stash  : [],
	filters: {},
	count  : 0,
	setup  : scrollViewSetup,
	watch  : scrollViewWatch,
	unwatch: scrollViewUnwatch,
	add    : scrollViewAdd,
	handler: scrollViewHandler
};

function scrollViewSetup() {
	this.add('.ui-scroll-view');
}

function scrollViewWatch() {
	pixiv.window
		.bind('scroll.scroll-view resize.scroll-view', pixiv.throttle(this.handler, this))
		.triggerHandler('scroll.scroll-view');
}

function scrollViewUnwatch() {
	pixiv.window.unbind('.scroll-view');
}

function scrollViewAddFilter(filter, callback) {
	this.filters[filter] = callback;
	return this;
}

function scrollViewAdd(element) {
	element = $(element);
	if (!element.length) return this;

	var exist = this.stash.length;
	this.stash = this.stash.concat(element.get());
	!exist && this.watch();
	return this;
}

function scrollViewHandler(e) {
	var w = pixiv.window,
		scroll_left   = w.scrollLeft(),
		scroll_right  = scroll_left + w.width(),
		scroll_top    = w.scrollTop(),
		scroll_bottom = scroll_top + w.height(),
		stash = this.stash,
		elements = [],
		element, target,
		filters = this.filters,
		filter, f, filter_name,
		i = 0, ii, offset, data;

	for (;element = stash[i]; ++i) {
		target = $(element);
		data = target.data();
		filter = data.filter;
		if (!filter) continue;

		offset = target.offset();
		if (
			offset.left >= scroll_left && offset.left < scroll_right &&
			offset.top >= scroll_top - 200 && offset.top < scroll_bottom + 500
		) {
			f = filter.split(/\s+/);
			for (ii = 0; filter_name = f[ii]; ++ii) {
				if (filters[filter_name] && filters[filter_name](target, e) === true) break;
			}
		}
		else {
			elements.push(element);
		}
	}
	this.stash = elements;
	!elements.length && this.unwatch();
}

pixiv.scrollView.filters['lazy-image'] = function(target, e) {
	var src = target.data('src');

	src && (target[0].nodeName == 'IMG' ?
		target.attr('src', src).load(function() {
			$(this).css('opacity', 1);
		}) :
		target.css('background-image', src)
	);
};


pixiv.ui.selectBox = {
	setup: selectBoxSetup
};

function selectBoxSetup() {
	$('select.ui-select-box').selectBox();
}

$.fn.selectBox = function(load_handler_global, select_handler_global) {
	return this.each(function() {
		var container = $(this),
			data = container.data(),
			initialized = !!data.initialized;

		if (initialized) return;

		var load_handler = data.loadHandler ? new Function('e', 'data', 'return (' + data.loadHandler + ')') : load_handler_global,
			select_handler = data.selectHandler ? new Function('e', 'data', 'return (' + data.selectHandler + ')') : select_handler_global;

		if (this.nodeName == 'SELECT') {
			var current = this.selectedIndex,
				options = this.options,
				_load_hander = load_handler,
				_select_handler = select_handler;

			select = container;
			container = $([
				'<div class="select-box-container" data-initialized="true">',
				'<div class="label group-modal-trigger">', options[current].innerHTML, '</div>',
				'<ul class="items group-modal"></ul>',
				'</div>'
			].join('')).insertBefore(this);

			load_handler = function(e, data) {
				var li, items = [];

				for (var i = 0, option; option = options[i]; ++i) {
					items[i] = '<li' + (i === current ? ' class="current"' : '') + ' data-index="' + i + '" data-value="' + option.value + '">' + option.innerHTML + '</li>';
				}
				li = $(items.join('')).appendTo(this);

				_load_hander && _load_hander.call(this, e, select.data());

				select_handler = function(e, data) {
					_select_handler && _select_handler.call(this, e, data);

					li
						.eq(current).removeClass('current').end()
						.eq(current = data.index).addClass('current');

					select[0].selectedIndex = current;
					select.change();
					return true;
				};
			};
		}

		var ul = $('ul.items', container);
		// TODO delegate
		container
			.click(function(e) {
				if (ul.is(':visible')) { // TODO
					pixiv.modal.close();
				}
				else {
					pixiv.modal.open(ul);
				}
				// ul.toggle();

				if (!initialized) {
					initialized = true;

					var label_container = $('div.label', this);

					load_handler.call(
						ul.delegate('li:not(.current)', 'click', function(e) {
							switch (select_handler.call(this, e, $(this).data())) {
							case true:
								label_container.text(this.innerHTML);
								break;

							case false:
								return false;
							}
							// update === true && label_container.text(this.innerHTML);
						})[0],
						e,
						$(this).data()
					);
				}
				return false;
			});
			// .mouseleave(function() { // TODO 画面外クリックで閉じるように
			// 	ul.hide();
			// });
	});
};	


pixiv.ui.tooltip = {
	container: null, // 外からの操作用
	setup    : uiTooltipSetup
};

function uiTooltipSetup() {
	var container = this.container = $('#ui-tooltip-container');

	if (container.length) {
		pixiv.document.delegate('.ui-tooltip', {
			mouseover: function(e) {
				var target = $(e.currentTarget),
					text = target.data('tooltip') || target.attr('title'),
					offset = target.offset();
				container
					.find('p').text(text).end()
					.show()
					.css({
						top : offset.top - container.outerHeight() - 3,
						left: offset.left + target.outerWidth() / 2 - container.outerWidth() / 2
					});
			},
			mouseout : function(e) {
				container.hide();
			}
		});
	}
}

pixiv.ui.shareButton = {
	container: [],
	template : null,
	setup    : uiShareButtonSetup,
	twitter  : uiShareButtonTwitter,
	facebook : uiShareButtonFacebook,
	open     : uiShareButtonOpen
};

function uiShareButtonSetup() {
	var self = this;
	this.template = $('#template-ui-share-container');

	$('ul.share-button')
		.find('.share-button-twitter').each(uiShareButtonTwitter).end()
		.find('.share-button-facebook').each(uiShareButtonFacebook).end()
		.find('.ui-share-button').click(function(e) { // TODO
			self.container[0] && self.container[0].is(':visible') ?
				pixiv.modal.close() :
				self.open(e);
		});

	$.getScript('https://apis.google.com/js/plusone.js');
}

function uiShareButtonTwitter() {
	var q = pixiv.queryString(
		$.extend({
			related: 'pixiv'
		}, $(this).data()), true
	);

	$('<iframe src="http://platform.twitter.com/widgets/tweet_button.html?' + q + '" frameborder="0" allowtransparency="true" scrolling="no"></iframe>').appendTo(this);
}

function uiShareButtonFacebook() {
	var q = pixiv.queryString(
		$.extend({
			app_id    : pixiv.config.facebookAppId,
			layout    : 'button_count',
			show_faces: 'false'
		}, $(this).data()), true
	);

	$('<iframe src="http://www.facebook.com/plugins/like.php?' + q + '" frameborder="0" allowtransparency="true" scrolling="no"></iframe>').appendTo(this);
}

function uiShareButtonOpen(e) {
	var target = $(e.target),
		data = target.data(),
		id = data.shareButtonId || 0,
		container = this.container[id] = this.container[id] || this.template.tmpl(data).appendTo('body'),
		offset = target.offset();

	pixiv.modal.open(
		container.css({
			top : offset.top + target.outerHeight() + 7,
			left: offset.left + target.outerWidth() / 2 - container.outerWidth() / 2
		})
	);

	if (!id) {
		$LAB
			.script('http://b.st-hatena.com/js/bookmark_button.js')
			.script('/stacc/modal.js');
	}

	return false;
}


pixiv.ad = {
	setup: adSetup,
	overture: {
		working: false,
		queue  : [],
		load   : overtureLoad
	}
};

function adSetup() {
	pixiv.modal.addBackground('#pageAdver, .adver_footer');
}


var overtureContextIds = [
	['pro0102', 0.125],
	['pro1900', 0.125],
	['spe0101', 0.125],
	//["pro0100", 0.1],
	['com1003', 0.125],
	['spo0000', 0.125],
	['com0600', 0.125],
	//["edu0100", 0.1],
	['edu0300', 0.125],
	['fin0205', 0.125]
];

function overtureLoad(id, options, data) {
	options = $.extend({
		type      : '',
		typeSuffix: null,
		max       : 2,
		explicit  : false,
		info      : null
	}, options);
	var overture = pixiv.ad.overture,
		queue = overture.queue,
		container;

	if (overture.working) {
		queue.push([id, options, data]);
	}
	else {
		container = $('#' + id);
		if (data) {
			options.max = options.max - data.length / 6;
		}
		if (options.max) {
			overture.working = true;
			container.addClass('loading-chobi');

			$.getScript(overtureMakeURL(options), function() {
				var d = w.zSr.slice(6);
				data && (d = d.concat(data));
				overtureShow(container.removeClass('loading-chobi'), d, options);

				overture.working = false;
				w.zCn  = undefined;
				w.zRef = undefined;
				w.zSr  = undefined;
				if (queue.length) {
					overtureLoad.apply(null, queue.shift());
				}
			});
		}
		else {
			overtureShow(container, data, options);
		}
	}
}

function overtureMakeURL(options) {
	var q = {
		ctxtUrl      : document.URL,
		ref          : document.referrer,
		ctxtCat      : 'default_business',
		mkt          : 'jp',
		maxCount     : options.max || 2,
		outputCharEnc: 'utf8'
	};
	var context_id;

	if (options.explicit) {
		q.ctxtId = 'pixiv_01';
		q.source = 'ecnavi_jp_pixiv_im_ron';
	}
	else {
		q.ctxtId = overtureContextId();
		q.source = 'ecnavi_jp_pixiv_im';
	}
	q.type = [options.type, pixiv.context.adOrder, pixiv.context.adNumber, context_id];
	options.typeSuffix && q.type.push(options.typeSuffix);
	q.type = q.type.join('_');

	return 'http://im.ecnavi.ov.yahoo.co.jp/js_flat/?' + pixiv.queryString(q);
}

function overtureContextId() {
	var value = Math.random(), v = 0, ret;
	for (var i = 0, c; c = overtureContextIds[i]; ++i) {
		v += c[1];
		if (v >= value) {
			ret = c[0];
			break;
		}
	}
	return ret || overtureContextIds[0][0];
}

function overtureShow(container, data, options) {
	if (!data) {
		return;
	}

	var ads = [];
	while (data.length) {
		var d = data.splice(0, 6),
			description = d[0],
			href        = d[2],
			title       = d[3],
			host        = d[4];

		ads.push([
			'<div>',
			'<a href="', href, '" target="_blank">',
			'<p class="title">', title, '</p>',
			'<p class="description">', description, '</p>',
			'<p class="host">', host, '</p>',
			'</a>',
			'</div>'
		].join(''));
	}
	var info = options.info === false ? '' : options.info || (options.explicit ?
		'PR' :
		'インタレストマッチ - <a href="http://ov.yahoo.co.jp/service/int/index.html?o=IM0028" target="_blank">広告の掲載について</a>');
	ads.push('<p class="info">' + info + '</p>');

	$(ads.join('')).prependTo(container);
}


pixiv.storage = {
	parse         : storageParse,
	addExpire     : storageAddExpire,
	config        : storageConfig,
	sessionStorage: storageSessionStorage,
	localStorage  : storageLocalStorage,
	storage       : storageStorage,
	cookie        : storageCookie,
	updateCookie  : storageUpdateCookie
};

function storageParse(d) {
	var data, expires;
	try {
		if (!isNaN(d)) {
			return d;
		}
		d = JSON.parse(d);
		if ($.type(d) == 'object') {
			expires = d.expires;
			data = expires || expires == 0 ?
				(+new Date > expires ? undefined : d.data) :
				d;
		}
		else {
			data = d;
		}
		return data;
	}
	catch (e) {
		return d;
	}
}

function storageAddExpire(data, expires) {
	return {data: data, expires: expires};
}

function storageConfig(id) {
	return function(name, value) {
		name = id + '_' + name;
		var options = {
			expires: +new Date + 7776000000, // 90 days
			path   : '/'
		};
		return value === undefined ?
			storageUpdateCookie(name, options) :
			storageCookie(name, value, options);
	};
}

function storageSessionStorage(name, value) {
	return storageStorage('session', name, value);
}

function storageLocalStorage(name, value) {
	return storageStorage('local', name, value);
}

function storageStorage(type, name, value) {
	var storage = w[type + 'Storage'], ret;

	if (!storage || !name || !$.support.json) return;

	switch (value) {
	case null:
		storage[name] = '';
		delete storage[name];
		break;

	case undefined:
		return pixiv.storage.parse(storage[name]);

	default:
		storage[name] = $.type(value) == 'object' ? JSON.stringify(value) : value;
	}
}

function storageCookie(name, value, options) {
	if (!'cookie' in d || !name) return;

	switch (value) {
		case undefined:
			var cookie = d.cookie;
			if (cookie && cookie != '') {
				var cookies = cookie.split(';');
				for (var i = 0, l = cookies.length, c; i < l; ++i) {
					c = $.trim(cookies[i]);
					if (c && c.indexOf(name + '=') == 0) {
						return decodeURIComponent(c.slice(name.length + 1));
					}
				}
			}
			break;

		default:
			options = options || {};
			if (value === null) {
				value = '';
				options.expires = -1;
			}

			var params = {
				expires: options.expires ?
					new Date(options.expires).toUTCString() :
					undefined,
				path   : options.path,
				domain : options.domain
			};
			var p = [], v;
			for (var k in params) {
				v = params[k];
				v && p.push(k + '=' + v);
			}
			options.secure && p.push('secure');
			p.unshift(encodeURIComponent(value));

			d.cookie = name + '=' + p.join(';');
	}
}

function storageUpdateCookie(name, options) {
	var value = storageCookie(name);
	value !== undefined && storageCookie(name, value, options);
	return value;
}


pixiv.scroll = function(position, speed, callback) {
	position = typeof position == 'string' ?
		$(position).offset().top :
		Number(position) || 0;
	var target = $($.browser.webkit ? 'body' : 'html').stop(true, true);
	if (speed === null) {
		pixiv.window
			.scrollTop(position)
			.trigger('pixiv.scrollComplete');
	}
	else {
		speed = speed || 800;
		pixiv.scroll.scrolling = true;
		target.animate({scrollTop: position}, speed, 'easeOutExpo', function() {
			pixiv.scroll.scrolling = false;
			if (callback) { // TODO use event
				callback();
			}
			pixiv.window.trigger('pixiv.scrollComplete');
		});
	}
	return false;
};

pixiv.scroll.scrolling = false;

pixiv.hashState = function(queries) {
	var k, q;
	if (queries === null) {
		// fx 3.0.x reloads page when hash is empty
		location.hash = '#';
		return null;
	}
	else if (!queries) {
		q = location.hash.slice(1);
		// fx decodes automatically
		if (!$.browser.mozilla) {
			q = decodeURIComponent(q);
		}
		return pixiv.hashState.parse(q);
	}
	else {
		q = pixiv.hashState.stringify(queries);
		location.hash = q;
		return q;
	}
};

pixiv.hashState.stringify = function(queries) {
	var k, v, ret = [];
	for (k in queries) {
		v = queries[k];
		if (typeof v != 'number' && !v || typeof v == 'function') {
			continue;
		}
		if (v === true) {
			ret.push(encodeURIComponent(k));
		}
		else {
			ret.push([encodeURIComponent(k), encodeURIComponent(queries[k])].join('='));
		}
	}
	return ret.join('&');
};

pixiv.hashState.parse = function(query) {
	var queries = query.split('&'),
		i = 0, q, m, key, value,
		ret = {};
	for (; q = queries[i]; ++i) {
		m = /^([^=]+)=?(.*)$/.exec(q) || [];
		if (m[1]) {
			key = decodeURIComponent(m[1]);
			value = m[2] && decodeURIComponent(m[2]);
			value = value ?
				isNaN(Number(value)) ? value : Number(value) :
				true;
			ret[key] = value;
		}
	}
	return ret;
};

pixiv.formatNumber = function(v, place) {
	place = place || 2;
	var n = v.toString().split('.')[0].length;
	while (n++ < place) {
		v = '0' + v;
	}
	return v;
};

var figure_separator = /^(-?\d+)(\d{3})/;

pixiv.figure = function(v) {
	v = v.toString();
	while (v != (v = v.replace(figure_separator, '$1,$2')));
	return v;
};

pixiv.preloadImage = function(var_args) {
	var paths = $.makeArray(arguments);
	for (var i = 0, path; path = paths[i]; ++i)
		document.createElement('img').src = path;
};


// TODO use jQuery.tmpl
pixiv.applyTemplate = (function() {
	var markup = /#\{([^|}]+)(?:\|(.*?)\|)?\}/g;
	return function(t, o, escape) {
		return (!t || !o) ?
			t :
			t.replace(markup, function(_, prop, alt) {
				prop = o[prop];
				if (!prop && prop !== '' && prop !== 0)
					prop = alt || '';
				return (escape === false) ? prop : prop.escapeTag();
			});
	};
})();

pixiv.getTemplate = function(id) {
	if (!id) {
		return null;
	}
	var template = $('#template-'+id);
	if (!template.length) {
		return null; //throw new Error('template-'+id+' not found.');
	}
	var t = $.trim(template.val());
	if (!template.hasClass('raw')) {
		t = t.replace(/[\r\n]/g, '');
	}
	return t;
};

pixiv.supportedInlineSVG = function() {
	var div = document.createElement('div');
	div.innerHTML = '<svg version="1.1" xmlns="http://www.w3.org/2000/svg"></svg>';
	return (div.childNodes[0].namespaceURI == 'http://www.w3.org/2000/svg');
};

// pixiv.findURL = findURL;
// 
// var find_url_pattern = /(https?:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)/g;
// 
// function findURL() {
// }

pixiv.searchURL = function(str, replace_urls) {
	// var url = /(https?:\/\/[\x21-\x7e]+)/gi,
	var url = /(https?:\/\/[-_.!~*\'()a-zA-Z0-9;\/?:\@&=+\$,%#]+)/g,
		i = 0, u, ret, urls;
	if (replace_urls) {
		replace_urls = $.makeArray(replace_urls);
		ret = str.replace(url, function(_, url) {
			return replace_urls[i++] || url;
		});
		return ret;
	}
	urls = str.match(url);
	if (!urls) {
		return urls;
	}
	ret = [];
	for (; u = urls[i]; ++i) {
		if ($.inArray(u, ret) == -1) {
			ret.push(u);
		}
	}
	return ret;
};

pixiv.truncate = function(str, to) {
	return str.length > to ? str.slice(0, to)+'...' : str;
};


(function(escapeHTML) {


pixiv.addURLLink = addURLLink;
pixiv.addHashTagLink = addHashTagLink;


//var url = /https?:\/\/\S+/g;
//var hash_tag = /(^|\s+)(#\S+)/g;
// ほぼtwitter風
var url = new RegExp("https?://[^/@\\s]+\\.([,.]?[-_!~*a-zA-Z0-9;/?:&=+$%#])+", "g");
var hash_tag = /(^|[^a-zA-Z0-9])(#[a-zA-Z0-9_]*[a-zA-Z_]+[a-zA-Z0-9_]*)/g;

function addURLLink(str) {
	return str.replace(url, function(url) {
		var href = pixiv.redirectURL(pixiv.unescapeHTML(url));
		href = escapeHTML(href);
		return '<a href="' + href + '" target="_blank">' + url + '</a>';
	});
};

function addHashTagLink(str) {
	return str.replace(hash_tag, function(_, separator, hash_tag) {
		var q = encodeURIComponent(pixiv.unescapeHTML(hash_tag));
		q = escapeHTML(q);
		return separator + '<a href="http://twitter.com/search?q=' + q + '" target="_blank">' + hash_tag + '</a>';
	});
};


})(pixiv.escapeHTML);


pixiv.redirectURL = function(url) {
	return pixiv.redirectURL.internal.test(url) ? encodeURI(url) : '/jump.php?' + encodeURIComponent(url);
};

pixiv.redirectURL.internal = /^https?:\/\/(?:.*\.?pixiv\.net|p\.tl)(?:\/|$)/;

pixiv.popupManager = {
	stash : [],

	setup: function() {
		if (document.addEventListener) {
			document.addEventListener('click', pixiv.popupManager.close, true);
		}
		else {
			$(document).click(pixiv.popupManager.close);
		}
	},

	register: function(handler) {
		if (typeof handler == 'function') {
			pixiv.popupManager.stash.push(handler);
		}
	},

	unregister: function(handler) {
		var stash = pixiv.popupManager.stash,
			i = 0, h;
		for (; h = stash[i]; ++i) {
			if (handler === h) {
				stash.splice(i, 1);
			}
		}
	},

	close: function(e) {
		var stash = pixiv.popupManager.stash,
			i = 0, handler;
		for (; handler = stash[i]; ++i) {
			handler(e);
		}
	}
};

pixiv.screen = {
	stash : [],

	setup: function() {
		$(window).click(function(e) {
			if (!$(e.target).parents('.dialog').length) // TODO お気に入り、マイピク申請部分を共通化して.popupに
				pixiv.screen.close();
		});
	},

	// TODO closeメソッドのみ登録すればいい
	register: function(screen) {
		if (typeof screen == 'object' && typeof screen.close == 'function')
			pixiv.screen.stash.push(screen);
	},

	unregister: function(screen) {
		var stash = pixiv.screen.stash;
		for (var i = 0, s; s = stash[i]; ++i) {
			if (screen === s)
				stash.splice(i, 1);
		}
	},

	close: function(ignore_screen) {
		var stash = pixiv.screen.stash;
		for (var i = 0, s; s = stash[i]; ++i) {
			if (s !== ignore_screen)
				s.close();
		}
	}
};

pixiv.dialog = {
	template: [
		'<div id="dialog">',
		'<div class="background" onclick="pixiv.dialog.close()"></div>',
		'<div class="main">',
		'<div class="close" onclick="pixiv.dialog.close()"></div>',
		'#{content}',
		'</div>',
		'</div>'
	].join(''),
	contents: {
		'mail-authentication': [
			'<p>メール認証が必要です</p>',
			'<form method="post" action="/mail_authentication.php">',
			'<input type="submit" value="認証用メールを送る">',
			'</form>'
		].join('')
	},

	setup: function() {
		if (!pixiv.user.noAuthenticated) return; // TMP contents has only one type yet
		$('.dialog').click(function() {
			var dialog = pixiv.dialog;
			var name = (/\s?dialog-(.+)\s?/.exec(this.className) || [])[1];
			var content = dialog.contents[name] || pixiv.getTemplate(name);
			if (content)
				dialog.open(content);
			return false;
		});
	},

	open: function(content) {
		if (!content) return null;
		var dialog = pixiv.dialog;
		var container = $(pixiv.applyTemplate(dialog.template, {
			content: content
		}, false))
			.appendTo('body')
			.find('.main');
		var w = $(window);
		var scroll_top = w.scrollTop();
		return container.css('top', Math.max(
			scroll_top + 10,
			scroll_top + w.height() / 2 - container.outerHeight(true) / 2
		));
	},

	close: function() {
		$('#dialog').remove();
		return false;
	}
};


pixiv.api = {
	error  : apiError,
	async  : apiAsync,
	get    : apiGet,
	post   : apiPost,
	request: apiRequest
};

function apiError(status) {
	pixiv.log('api error', status);
}

function apiAsync(data) {
	var d = $.Deferred();
	setTimeout(function() {
		d.resolve(data, true);
	});
	return d;
}

function apiGet(url, q, options) {
	return this.request('GET', url, q, options);
}

function apiPost(url, q, options) {
	return this.request('POST', url, q, options);
}

// can not use JSONP
function apiRequest(method, url, q, options) {
	options = options || {};
	var supported = $.support.storage,
		cache = options.cache,
		name, data, callback;

	if (supported && cache) {
		name = method + url; q && (name += $.param(q));

		switch ($.type(cache)) {
		case 'object':
			data = cache[name];
			!data && (callback = function(data) {
				cache[name] = data;
			});
			break;

		case 'number':
			data = pixiv.storage.localStorage(name);
			!data && (callback = function(data) {
				pixiv.storage.localStorage(name, pixiv.storage.addExpire(data, cache));
			});
			break;

		default:
			data = pixiv.storage.sessionStorage(name);
			!data && (callback = function(data) {
				pixiv.storage.sessionStorage(name, data);
			});
		}
		if (data) {
			return this.async(data);
		}
	}

	return $.ajax($.extend({
		type    : method,
		url     : url,
		data    : q,
		dataType: 'json'
	}, options.ajax)).then(callback, this.error);
}

$.extend(pixiv.api, {
	pTl: function(url) {
		var options = {
			ajax : {dataType: 'jsonp'},
			cache: true
		};
		return pixiv.api.get('http://p.tl/api/api_simple.php', {
			url: url,
			key: pixiv.config.pTlAPIKey
		}, options);
	},

	suggest: function(keyword) {
		return pixiv.api.get('/rpc_cps.php', {keyword: keyword}, {cache: +new Date + 1000 * 60 * 60 * 24});
	},

	recommender: {
		request: function(type, options) {
			return pixiv.api.get('/rpc_recommender.php', $.extend({
				type: type
			}, options));
		},

		user: function(user, count, comment) {
			return pixiv.api.recommender.request('user', {
				sample_users       : user,
				num_recommendations: count || 10,
				nc                 : Number(comment) || 0
			});
		},

		hideUser: function(id) {
			return pixiv.api.post('/rpc_recommender.php', {
				type          : 'user',
				op            : 'hide',
				ignore_user_id: id
			});
		}
	},

	group: {
		request: function(mode, type, id) {
			return pixiv.api.post('/rpc_group_setting.php', {
				mode: mode,
				type: type,
				id  : id
			});
		},

		getMyPixivList: function() {
			return pixiv.api.group.getList('mypixiv');
		},

		getFavoriteList: function() {
			return pixiv.api.group.getList('bookuser');
		},

		getList: function(type) {
			return pixiv.api.group.request('get', type, pixiv.user.id);
		},

		removeMyPixiv: function(id) {
			return pixiv.api.group.remove('mypixiv', id);
		},

		removeFavorite: function(id) {
			return pixiv.api.group.remove('bookuser', id);
		},

		remove: function(type, id) {
			return pixiv.api.group.request('del', type, id);
		}
	},

	event: {
		stash: {},

		request: function(mode, type, id) {
			return pixiv.api.post('/event_add.php', {
				mode: mode,
				type: type,
				id  : id
			});
		},

		deleteImage: function(type, id) {
			return pixiv.api.event.request('delete_img', type, id);
		},

		getCalendar: function(year, month) {
			return pixiv.api.post('/rpc_event_calendar.php', {
				y: year,
				m: month
			}, {cache: pixiv.api.event.stash});
		}
	}
});


// TODO replace $.fn.selectbox
pixiv.SelectBox = function(select, callback) {
	this.select = select;
	this.callback = callback;
	this.proxy();
};

pixiv.SelectBox.prototype = {
	select           : null,
	options          : null,
	selectedContainer: null,
	currentItem      : null,
	template: [
		'<div class="select-box">',
		'<div class="selected">#{selected}</div>',
		'<ul class="items" style="display: none;">#{item}</ul>',
		'</div>'
	].join(''),
	itemTemplate: '<li class="#{klass}" data-value="#{value}">#{item}</li>',

	proxy: function() {
		if ($.browser.touchDevice) {
			$(this.select).show();
			return;
		}
		var select = this.select,
			index = select.selectedIndex,
			items = [],
			i = 0, option, options = select.options;
		for (; option = options[i]; ++i) {
			items[i] = pixiv.applyTemplate(this.itemTemplate, {
				klass: 'option'+(i === index ? ' current' : ''),
				value: option.value,
				item : option.innerHTML
			});
		}
		var select_box = $(pixiv.applyTemplate(this.template, {
			selected: options[index].innerHTML,
			item    : items.join('')
		}, false));
		var item_container = $('ul.items', select_box);
		select_box.hover(
			function() { item_container.show(); },
			function() { item_container.hide(); }
		);
		this.selectedContainer = $('div.selected', select_box);
		this.currentItem = $('li', select_box)
			.click(this.click.bind(this))
			.eq(index);
		$(select)
			.hide()
			.after(select_box);
		if (this.callback) {
			this.callback();
		}
	},

	click: function(e) {
		var self = $(e.target),
			current_item = this.currentItem;
		if (e.target !== current_item[0]) {
			current_item.removeClass('current');
			this.currentItem = self.addClass('current');
			this.selectedContainer.text(self.text());
			$(this.select)
				.val(self.data('value'))
				.change();
		}
		self.mouseleave();
	}
};


pixiv.Favorite = function() {};

pixiv.Favorite.prototype = {
	name      : 'favorite',
	type      : 'bookuser',
	preference: null,
	button    : null,
	groups    : null,

	initialize: function() {
		this.preference = $('#favorite-preference');
		this.button = $('#favorite-button').click(this.toggle.bind(this));
	},

	toggle: function() {
		(this.preference.is(':visible')) ?
			this.close() :
			this.open();
		return false;
	},

	open: function() {
		pixiv.screen.close(this);
		if (!this.groups)
			this.initializePreferenceContainer();
		this.preference.show();
		var button = this.button;
		if (button.hasClass('added'))
			this.button.addClass('open');
	},

	initializePreferenceContainer: function() {
		var self = this;
		var preference = this.preference;
		pixiv.screen.register(this);
		$('div.close', preference).click(this.close.bind(this));
		$('input.remove', preference).click(this.remove.bind(this));
		$('select', preference).change(function(e) {
			if (this.value == 'new' && this.selectedIndex == 1)
				self.addGroup();
		});
		setTimeout(function() { // ?
			pixiv.api.group.getList(self.type).done(function(data) {
				// 今どのグループに所属しているかは分からない
				var tags = data.tag_a;
				var groups;
				// TODO API側を変える？
				if ($.isArray(tags))
					groups = tags;
				else {
					groups = [];
					for (var k in tags) groups.push(k);
				}
				self.groups = groups;
				$('select', preference)
					.append(self.makeGroup(groups))
					.parent().removeClass('loading').end()
					[0].disabled = false;
			});
		});
	},

	makeGroup: function(groups) {
		if (!$.isArray(groups)) groups = [groups];
		var option = [];
		for (var i = 0, group; group = groups[i]; ++i) {
			group = group.escapeTag();
			option[i] = '<option value="'+group+'">'+group+'</option>';
		}
		return option.join('');
	},

	addGroup: function() {
		var group = window.prompt('新規グループ名を指定してください');
		if (!group) return;
		group = $.trim(group.replace(/ +/g, ''));
		if (!group) return;

		this.groups.push(group);
		this.groups.sort();

		var position = $.inArray(group, this.groups);
		position = (position == -1) ? 1 : position + 1;
		$(this.makeGroup(group))
			.insertAfter($('option', this.preference).eq(position))
			[0].selected = true;
	},

	close: function() {
		this.preference.hide();
		this.button.removeClass('open');
		return false;
	},

	add: function() {
		// nothig yet
	},

	remove: function() {
		pixiv.api.group.remove(this.type, pixiv.context.userId);
			// .next(function() {
			// 	$('#group-status')
			// 		.text('外しました')
			// 		.show()
			// 		.fadeOut(1500);
			// });
		this.removed();
	},

	removed: function() {
		$('#favorite-button')
			.removeClass('added')
			.attr('title', 'お気に入り追加');
		$('form', this.preference)
			.attr('action', '/bookmark_add.php')
			.append('<input type="hidden" name="mode" value="add">')
			.find('input.remove').remove();
		this.close();
	}
};


pixiv.MyPixiv = function() {};

pixiv.MyPixiv.prototype = $.extend(new pixiv.Favorite, {
	name: 'mypixiv',
	type: 'mypixiv',

	initialize: function() {
		this.preference = $('#mypixiv-preference');
		this.button = $('#mypixiv-button');
		if (pixiv.context.myPixiv)
			this.button.click(this.toggle.bind(this));
	},

	removed: function() {
		$('#mypixiv-button')
			.removeClass('added')
			.attr('title', 'マイピク申請');
		this.button.unbind('click');
		this.close();
	}
});


pixiv.Popup = function(context) {
	this.context = context;
	$('.trigger', context).click(this.toggle.bind(this));
};

pixiv.Popup.setup = function() {
	$('.popup').each(function() {
		new pixiv.Popup(this);
	});
};

pixiv.Popup.prototype = {
	context  : null,
	container: null,

	load: function() {
		this.container = $('.container', this.context)
			.find('.close').click(this.close.bind(this)).end();
		pixiv.screen.register(this);
	},

	toggle: function() {
		if (!this.container)
			this.load();
		return (this.container.is(':visible')) ?
			this.close() :
			this.open();
	},

	open: function() {
		pixiv.screen.close(this);
		var input = this.container
			.show()
			.find(':text, textarea')[0];
		if (input)
			input.focus();
		if (typeof this.openComplete == 'function')
			this.openComplete();
		return false;
	},

	openComplete: null,

	close: function() {
		this.container.hide();
		if (typeof this.closeComplete == 'function')
			this.closeComplete();
		return false;
	},

	closeComplete: null
};

pixiv.EventTracker = {
	setup: function(){
		if (location.pathname.indexOf('/novel') != 0) {
			$('a[href*="novel"]').click(function(){
				try {
					_gaq.push(['_trackEvent', 'novel', 'JumpToNovel', location.pathname]);
				} 
				catch (e) {
				}
			});
		}
		if (location.pathname == '/bookmark.php' && location.search.match(/type=user/)) {
			$('.msgbox_bottom input[type="submit"]').click(function(){
				try {
					_gaq.push(['_trackEvent', 'pixiv', 'ModBookmarkUser', $(this).attr('name'), $('.list_box input:checked').length]);
				} 
				catch (e) {
				}
			});
		}
		if (location.pathname == '/mypixiv_all.php') {
			$('.msgbox_bottom input[type="submit"]').click(function(){
				try {
					_gaq.push(['_trackEvent', 'pixiv', 'ModMypixivUser', $(this).attr('name'), $('.list_box input:checked').length]);
				} 
				catch (e) {
				}
			});
		}
	}
};

if (!window.pixiv.page) { pixiv.page = {}; } // TODO move to initialize.js
if (!window.pixiv.pageModule) { pixiv.pageModule = {}; } // TODO move to initialize.js

pixiv.pageModule.tweetButton = function() {
	$(function() {
		$LAB.script('http://platform.twitter.com/widgets.js');
	});
};

pixiv.pageModule.twitterWidget = function() {
	$(function() {
		$LAB
			.script('http://widgets.twimg.com/j/2/widget.js')
			.wait(function() {
				if (pixiv.context.twitterWidgetOptions) {
					new TWTR.Widget(pixiv.context.twitterWidgetOptions).render().start();
				}
			});
	});
};

pixiv.pageModule.circleList = function() {
	$LAB.script('/modules/circle_list.js?20110614');
};


// $.extend(pixiv.page, {
// 	'index': function() {
// 		$('div.facebook-like-box').each(pixiv.widget.facebookLikeBox);
// 	}
// });


pixiv.page['setting_design'] = function() {
	// TODO use farbtastic: http://acko.net/dev/farbtastic
	return $LAB
		// .script('http://ajax.googleapis.com/ajax/libs/prototype/1.6.1.0/prototype.js').wait()
		.script('http://ajax.googleapis.com/ajax/libs/scriptaculous/1.8.3/builder.js').wait()
		.script('http://ajax.googleapis.com/ajax/libs/scriptaculous/1.8.3/effects.js').wait()
		.script('http://ajax.googleapis.com/ajax/libs/scriptaculous/1.8.3/dragdrop.js').wait()
		.script('http://ajax.googleapis.com/ajax/libs/scriptaculous/1.8.3/slider.js').wait()
		.script('/lib/colorpicker/yahoo.color.js').wait()
		.script('/lib/colorpicker/colorPicker.js').wait()
		.script('/setting_design.js');
};

pixiv.page['bookmark?type=user'] = function() {
	if (pixiv.user.premium)
		$LAB.script('/add_group.js');
};

pixiv.page['member_illust'] = function() {
	// FIXME
	if (/mode=manga/.test(location.search)) {
		return;
	}

	$LAB
		// .script('http://ajax.googleapis.com/ajax/libs/prototype/1.6.1.0/prototype.js').wait()
		.script('https://ajax.googleapis.com/ajax/libs/scriptaculous/1.8.3/effects.js')
		.script('/rpc.js').wait()
		.script('/member_illust.js?20110627')
		.script('/modules/rating.js?20101107', '/tag_edit.js');
};

pixiv.page['novel/show'] = function() {
	$LAB
		// .script('http://ajax.googleapis.com/ajax/libs/prototype/1.6.1.0/prototype.js').wait()
		.script('https://ajax.googleapis.com/ajax/libs/scriptaculous/1.8.3/effects.js')
		.script('/rpc.js').wait()
		.script('/member_illust.js?20110627')
		.script('/modules/rating.js?20101107', '/tag_edit.js');
};

pixiv.page['ranking'] = function() {
	return $LAB
		.script('/ranking.js?20110627')
		.wait(function() {
			$(function() {
				pixiv.page.ranking.setup();
			});
		});
};

pixiv.page['search_user'] = function() {
	$(function() {
		pixiv.userRecommend.setup();
	});
};

pixiv.page.rankingLog = function() {
	return $LAB
		.script('/ranking_log.js')
		.wait(function() {
			$(function() {
				pixiv.page.rankingLog.setup();
			});
		});
};

// pixiv.page.stacc = function() {
// 	return $LAB
// 		.script('/stacc.index.js?20101227')
// 		.wait(function() {
// 			$(function() {
// 				// $LAB.script('http://platform.twitter.com/widgets.js');
// 				pixiv.page.stacc.setup();
// 			});
// 		});
// };

pixiv.page.eventMember = function() {
	return $LAB
		.script('/event_member.js?20110614')
		.wait(function() {
			$(function() {
				pixiv.myList.setup();
			});
		});
};


pixiv.setup();


})(this, document, jQuery);
