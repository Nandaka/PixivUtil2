(function(w, d, $) {


pixiv.manga = {
	config      : null,
	offset      : 200,
	defaultView : 'scroll',
	view        : 'scroll',
	position    : 0,
	/**
		0. no setup: loading = null
		1. no loading: loaded[position] = undefined
		2. loading: loaded[position] = [true, false] ([0]: loaded, [1]: still loading)
		3. loaded: loaded[position] = true
	 */
	loaded      : null,
	fixed       : [],
	lastUpdated : 0,
	/**
		cache
	 */
	windowHeight: 0,
	imageContainer     : null,
	controlContainer   : null,
	pageNumberContainer: null,
	pageNumberTemplate : null,

	setup: function() {
		var self = this;
		this.imageContainer = $('div.image-container');
		this.controlContainer = $('nav#control-container');
		this.pageNumberContainer = $('aside#page-number');
		this.pageNumberTemplate = $('#template-page-number');
		this.config = pixiv.storage.config('member_illust_manga');

		var view = this.defaultView = this.view = this.config('view') || this.defaultView;

		if ($.browser.touchDevice) {
			// TODO apply all pages
			$('body').addClass('touch-device');
		}
		else {
			if (w.opener) {
				$('li#window-close').css('display', 'inline');
			}
			pixiv.shortcut
				.bind('j', this.next)
				.bind('k', this.prev)
				.bind('o', this.openFullSizeImage)
				.bind('z', this.toggleView)
				.bind(13, function() {
					if (self.view == 'thumbnail') {
						pixiv.shortcut.trigger('z');
					}
				});
		}

		if (view == 'slide') {
			pixiv.window
				.bind('changePosition', function() {
					self.updatePageNumber();
					self.showImage();
				})
				.resize(this.updateWindowHeight)
				.resize()
				.trigger('changePosition');
		}
		else {
			this.loaded = new Array(pixiv.context.images.length);
			this.fixed = $.makeArray(this.loaded);
			pixiv.window
				.bind('changePosition', this.updatePageNumber)
				.bind('changePosition.updateImageHeight', this.updateImageHeight)
				.bind('changePosition.loadImage', this.loadImage)
				.bind('pixiv.scrollComplete', this.scroll)
				.resize(this.updateWindowHeight)
				.scroll(this.scroll)
				.resize()
				.scroll();
		}

		pixiv.rating.setup();
		pixiv.questionnaire.setup();
	},

	thumbnailImage: function(src) {
		return src.replace(/(\/impostore)(\/\d+)(_p\d+)/, '$1/mobile$2_128x128$3');
	},

	permalink: function(page_number) {
		var q = {
			mode     : 'manga_big',
			illust_id: pixiv.context.illustId,
			page     : page_number - 1
		};
		return '/member_illust.php?'+$.param(q);
	},

	pageNumber: function(src) {
		return Number((/p(\d+)\.\w+(\?|$)/.exec(src) || [])[1]) + 1;
	},

	ok: function(list) {
		if (!list.length) {
			return false;
		}
		for (var i = 0, a; a = list[i]; ++i) {}
		return i == list.length;
	},

	eachImage: function(position, f) {
		if (typeof position == 'function') {
			f = position;
			position = undefined;
		}
		position = position || this.position;
		var sources = pixiv.context.images[position];
		for (var i = 0, source; source = sources[i]; ++i) {
			f(i, this.pageNumber(source));
		}
	},

	findPosition: function(page_index) {
		var current = 0;
		for (var i = 0, images = pixiv.context.images, sources; sources = images[i]; ++i) {
			for (var ii = 0, ll = sources.length; ii < ll; ++ii) {
				if (current == page_index) {
					return i;
				}
				++current;
			}
		}
		return -1;
	},

	imageTop: function(offset) {
		offset = offset || 0;
		var scroll_top = pixiv.window.scrollTop(),
			top = Math.ceil(this.imageContainer.eq(this.position).position().top); // [fx]
		return scroll_top <= top + offset;
	},

	updateWindowHeight: function() {
		pixiv.manga.windowHeight = pixiv.window.height();
		var image_container = pixiv.manga.imageContainer;
		if (image_container.length > 1) {
			var body = $('body');
			var bottom = pixiv.manga.windowHeight - (body.height() - image_container.last().offset().top) + image_container.last().outerHeight();
			body.css('padding-bottom', Math.max(bottom, 100));
			image_container = image_container.slice(0, -1);
		}
		image_container.css('min-height', pixiv.manga.windowHeight - 64);
	},

	updateNavigationPosition: function() {
		var self = pixiv.manga;
		var scroll_top = pixiv.window.scrollTop();
		self.updateWindowHeight();
		self.controlContainer.css('top', scroll_top + 10);
		self.pageNumberContainer.css('top', scroll_top + window.innerHeight - 10 - self.pageNumberContainer.outerHeight(true));
	},

	updatePosition: function(position) {
		if (position || position == 0) {
			if (position != this.position) {
				this.position = position;
				pixiv.window.trigger('changePosition');
			}
			return this;
		}

		var scroll_top = pixiv.window.scrollTop(),
			offset = this.offset,
			image_container = this.imageContainer;
		for (var i = 0, l = image_container.length; i < l; ++i) {
			var container = image_container.eq(i),
				top = container.position().top,
				height = container.innerHeight(),
				scroll_bottom = top + height;
			if (scroll_top >= top && scroll_top <= scroll_bottom) {
				this.position = i;
				pixiv.window.trigger('changePosition');
				break;
			}
		}
		return this;
	},

	updatePageNumber: function() {
		var self = pixiv.manga;
		var total_pages = pixiv.context.totalPages;
		var sources = pixiv.context.images[self.position];
		var page_number = self.pageNumber,
			permalink = self.permalink;
		var data = {
			current_pages: [],
			total        : total_pages
		};
		var pages = [];
		for (var i = 0, src; src = sources[i]; ++i) {
			var page = page_number(src);
			data.current_pages[i] = {
				src : permalink(page),
				page: page
			};
			pages.push(page);
		}
		self.pageNumberTemplate
			.tmpl(data)
			.appendTo(self.pageNumberContainer.empty());

		document.title = pixiv.context.title+' ['+pages.join(', ')+']';
	},

	updateImageHeight: function() {
		var self = pixiv.manga;
		var image_container = self.imageContainer,
			start = self.position,
			end = pixiv.context.images.length;
		if (start != 0 && !self.imageTop()) {
			++start;
		}
		for (var n = start; n < end; ++n) {
			if (self.loaded[n] === true && !self.fixed[n]) {
				image_container.eq(n).removeClass('placeholder');
				self.fixed[n] = true;
			}
		}
		if (self.ok(self.fixed)) {
			pixiv.window.unbind('changePosition.updateImageHeight');
			// end
		}
	},

	loadImage: function() {
		var self = pixiv.manga,
			loaded = self.loaded,
			position = self.position,
			image_container = self.imageContainer,
			images = pixiv.context.images;
		var start = Math.max(0, position - 1),
			end = Math.min(position + 2, image_container.length);
		for (var n = start; n < end; ++n) {
			if (!loaded[n]) {
				var img = $('img', image_container[n]),
					img_length = img.length;
				loaded[n] = new Array(img_length);
				for (var i = 0; i < img_length; ++i) {
					img.eq(i)
						.addClass('loading')
						.load({i: i, position: n}, self.loadImageHandler)
						.attr('src', pixiv.context.images[n][i] || ''); // [ie] must be run after load
				}
			}
		}		
	},

	showImage: function() {
		var image_container = this.imageContainer,
			position = this.position;
		var sources = pixiv.context.images[position], source_length = sources.length;
		var img = $('img', image_container);
		img[0].src = sources[0];
		if (source_length == 2) {
			if (img.length == 2) {
				img.show();
			}
			else {
				img = img.add($('<img onclick="pixiv.manga.next()"/>').appendTo(image_container));
			}
			img[1].src = sources[1];
		}
		else {
			img.eq(1).hide();
		}

		var klass = ['image-container'];
		$.inArray(position, pixiv.context.spreadImages) != -1 && klass.push('spread');
		position == 0 && klass.push('first');
		position == pixiv.context.images.length - 1 && klass.push('last') && source_length == 1 && klass.push('odd');
		image_container[0].className = klass.join(' ');
	},

	loadImageHandler: function(e) {
		var self = pixiv.manga;

		this.className = '';

		var loaded = self.loaded,
			position = e.data.position,
			loaded_list = loaded[position];
		loaded_list[e.data.i] = true;
		if (self.ok(loaded_list)) {
			loaded[position] = true;
			if (self.ok(loaded)) {
				pixiv.window.unbind('changePosition.checkImage');
				// end
			}
			self.updateImageHeight();
		}
	},

	scroll: function() {
		var self = pixiv.manga;
		if ($.browser.touchDevice) {
			self.updatePosition();
			self.updateNavigationPosition();
		}
		else {
			if (pixiv.scroll.scrolling || self.view != 'scroll') {
				return;
			}
			var now = +new Date;
			if (now - self.lastUpdated >= 50) {
				self.lastUpdated = now;
				self.updatePosition();
			}
		}
	},

	scrollTo: function(top, speed, callback) {
		speed = !speed && speed != 0 || $.browser.msie8 ? null : speed;
		pixiv.scroll(top, speed, callback);
	},

	move: function(position) {
		var view = this.view;

		this.updatePosition(position);
		if (view == 'scroll') {
			this.lastUpdated = +new Date; // cancel scroll event
			this.scrollTo(this.imageContainer.eq(position).position().top, 100);
		}
		else if (view == 'thumbnail') {
			this.thumbnail.updateCurrentPosition();
		}

		return this;
	},

	current: function() {
		this.move(this.position);
	},

	prev: function() {
		var self = pixiv.manga;
		if (self.view != 'scroll' || self.view == 'scroll' && self.imageTop()) {
			var prev_position = self.position - 1;
			if (prev_position >= 0) {
				self.move(prev_position);
			}
		}
		else {
			self.current();
		}
	},

	next: function() {
		var self = pixiv.manga;
		var position = self.position;
		var next_position = position + 1;
		if (next_position < pixiv.context.images.length) {
			self.move(next_position);
		}
		else if (self.view == 'scroll') {
			self.scrollTo($('body').outerHeight(true) - self.windowHeight, 300);
		}
	},

	changeView: function(view) {
		view = view || (pixiv.manga.defaultView == 'scroll' ? 'slide' : 'scroll');
		pixiv.manga.config('view', view);
		pixiv.scroll(0, null);
		location.reload();
	},

	toggleView: function() {
		var self = pixiv.manga;
		var body = $('body');
		if (self.view == 'thumbnail') {
			body.removeClass('thumbnail-view');
			self.view = self.defaultView;
			self.current();
		}
		else {
			body.addClass('thumbnail-view');
			self.view = 'thumbnail';
			pixiv.manga.thumbnail.show();
			if ($.browser.touchDevice) {
				self.updateNavigationPosition();
			}
		}
		return self;
	},

	openFullSizeImage: function(position) {
		pixiv.manga.eachImage(position, function(i, page_number) {
			window.open(pixiv.manga.permalink(page_number));
		});
	},

	favorite: function() {
		window.open('/bookmark_add.php?type=illust&illust_id='+pixiv.context.illustId);
	}
};


pixiv.manga.thumbnail = {
	thumbnailContainer: null,
	thumbnailListContainer: null,

	setup: function() {
		this.thumbnailContainer = $('section#thumbnail');
	},

	thumbnailImage: function(page_number) {
		return pixiv.context.images[0][0].replace(/(\/\w+)_p\d+\.\w+/, '/mobile$1_128x128_p'+page_number+'.jpg');
	},

	updateCurrentPosition: function() {
		var li = $('li', pixiv.manga.thumbnail.thumbnailListContainer).removeClass('current');
		pixiv.manga.eachImage(function(i, page_number) {
			li.eq(page_number - 1).addClass('current');
		});
	},

	go: function(page_index) {
		pixiv.manga
			.updatePosition(pixiv.manga.findPosition(page_index))
			.toggleView();
	},

	show: function() {
		if (this.thumbnailListContainer) {
			this.thumbnailListContainer.show();
			this.updateCurrentPosition();
			pixiv.window.scrollTop(0);
			return;
		}

		this.setup();

		var images = [];
		for (var i = 0, l = pixiv.context.totalPages; i < l; ++i) {
			images[i] = this.thumbnailImage(i);
		}
		$('#template-thumbnail-view-list')
			.tmpl({ images: images })
			.appendTo(this.thumbnailContainer);

		this.thumbnailListContainer = $('ul#thumbnail-list');
		this.show();
	}
};


pixiv.api.rating = function(rate) {
	var q = {
		mode : 'save',
		i_id : pixiv.context.illustId,
		u_id : pixiv.user.id,
		qr   : pixiv.context.questionnaire,
		score: rate
	};
	return pixiv.api.post('/rpc_rating.php', q);
};

pixiv.api.questionnaire = function(n) {
	var q = {
		mode: 'save2',
		i_id: pixiv.context.illustId,
		u_id: pixiv.user.id,
		qr  : Number(pixiv.context.hasQuestionnaire),
		num : n
	};
	return pixiv.api.post('/rpc_rating.php', q);
};


pixiv.rating = {
	rate: 0,
	rateContainer  : null,
	statusContainer: null,

	setup: function() {
		var self = this;

		if (pixiv.context.rated) { return; }

		this.rateContainer = $('div.rate-container')
			.mousemove(function(e) {
				var container = $(this);
				var rate = Math.ceil((e.pageX - container.position().left + 1) / 260 * 10);
				if (rate != self.rate) {
					container
						.removeClass('rate-'+self.rate)
						.addClass('rate-'+rate);
					self.rate = rate;
				}
			})
			.mouseleave(function() {
				$(this).removeClass('rate-'+self.rate);
				self.rate = 0;
			})
			.click(this.rate);

		this.statusContainer = $('div.status', this.rateContainer);
	},

	rate: function(e) {
		var self = pixiv.rating;
		var rate = self.rate;

		if (!rate || rate > 10) { return false; }
		pixiv.api.rating(rate);

		var status_container = self.statusContainer.text(rate);
		status_container
			.css('left', 26 * rate - 13 - status_container.width() / 2)
			.animate({
				marginTop: -20,
				opacity  : 0
			}, 'slow', function() {
				status_container.remove();
			});

		self.rateContainer
			.addClass('rated rate-'+rate)
			.unbind();
		pixiv.context.rated = true;

		return false;
	}
};


pixiv.questionnaire = {
	container                   : null,
	statusContainer             : null,
	questionnaireContainer      : null,
	questionnaireResultContainer: null,

	setup: function() {
		if (!pixiv.context.hasQuestionnaire) {
			return;
		}

		var container = this.container = $('div.questionnaire-container');
		this.statusContainer = $('p.status', container);
		this.questionnaireContainer = $('div.questionnaire', container);
		this.questionnaireResultContainer = $('div.questionnaire-result', container);
	},

	send: function(n) {
		var self = this;

		this.toggleQuestionnaire();
		this.statusContainer.text('...');

		pixiv.api.questionnaire(n).done(function(data) {
			/**
				data: { html: string, keyword: string }
			 */
			var questionnaire_result_container = $('span.q'+n, self.questionnaireResultContainer);
			questionnaire_result_container.text(+questionnaire_result_container.text() + 1);
			self.toggleResult();

			$('#template-questionnaire-result')
				.tmpl({ result: data.keyword })
				.appendTo(self.statusContainer.empty());
		});
	},

	toggleResult: function() {
		this.questionnaireResultContainer.toggle();
	},

	toggleQuestionnaire: function() {
		this.questionnaireContainer.toggle();
	}
};


})(this, document, jQuery);
