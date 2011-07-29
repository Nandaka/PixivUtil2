if (typeof adingoDA0049600011 == 'undefined') {
    var adingoDA0049600011 = null;
}
var hybridPlus0049600011 = {
    keywordSets : [{"word":"\u6d6e\u6c17\u8abf\u67fb","ref":"HS%7Cbookmarkmain%7CORG%7C1efd7f98aeea09b2e6c0c7316d17b480"},{"word":"\u526f\u53ce\u5165","ref":"HS%7Cbookmarkmain%7CORG%7Cb8ad555291cac1cd9590bb4e1e4d2112"},{"word":"\u751f\u7406\u4e0d\u9806","ref":"HS%7Cbookmarkmain%7CORG%7C425e69afe25d1ac16c3372669d588cc5"},{"word":"\u4e0d\u767b\u6821","ref":"HS%7Cbookmarkmain%7CORG%7Cdcaeff4a8d9d61240386a3636742d9d1"},{"word":"\u97d3\u56fd\u8a9e","ref":"HS%7Cbookmarkmain%7CORG%7C2f263bd0cea04db47be19883cb396671"},{"word":"\u751f\u7406\u75db \u7de9\u548c","ref":"HS%7Cbookmarkmain%7CORG%7C53c2f7ce426259cf007e92471c994079"},{"word":"\u4e2d\u56fd\u8a9e","ref":"HS%7Cbookmarkmain%7CORG%7C1e645cea1dc60628c83078963431dbca"},{"word":"\u304a\u898b\u5408\u3044\u30d1\u30fc\u30c6\u30a3\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Ce4c27f8af5449abde50ad34772aad41c"},{"word":"\u5a5a\u6d3b\u5408\u30b3\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7Cf9a714d1bc23ae789989dcdaf8042c00"},{"word":"\u80a5\u6e80\u6cbb\u7642","ref":"HS%7Cbookmarkmain%7CORG%7C0d6293633efc4f2a3d6b7fed90ee548f"},{"word":"\u30a4\u30f3\u30d7\u30e9\u30f3\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7Cd50de8c9e0ced3dc61400c5f2948e1ac"},{"word":"DVD\u30ec\u30f3\u30bf\u30eb","ref":"HS%7Cbookmarkmain%7CORG%7C8ce17a796aab0e7a25ec8571985e7875"},{"word":"\u60a9\u307f\u76f8\u8ac7","ref":"HS%7Cbookmarkmain%7CORG%7C5b7728fac0d7e58b670ff343cf8ed7e9"},{"word":"\u591a\u6c57","ref":"HS%7Cbookmarkmain%7CORG%7C12f078582067b3b03ba297d3af016b58"},{"word":"\u30c7\u30fc\u30bf\u5165\u529b","ref":"HS%7Cbookmarkmain%7CORG%7Cfa9a1582366ded9414e71c212ce75cb6"},{"word":"\u30da\u30f3\u30bf\u30d6\u30ec\u30c3\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7Ca7c562279555211c838d6dfd1edeadaa"},{"word":"\u30c7\u30b6\u30a4\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Caa6851ddfa494e996cd98066e3e7c758"},{"word":"\u7d50\u5a5a","ref":"HS%7Cbookmarkmain%7CORG%7C51769a9529e535f37b813fca74b6aa9a"},{"word":"\u30d5\u30a9\u30c8\u30b7\u30e7\u30c3\u30d7","ref":"HS%7Cbookmarkmain%7CORG%7Cb76fd13c428456f2cf4258d687532025"},{"word":"\u7121\u6599 \u30d5\u30a1\u30a4\u30eb\u30b5\u30fc\u30d0\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C4867c8f543cd8ea032be84e20981e851"},{"word":"\u30c7\u30b6\u30a4\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C3513a0b7810412840f1b60fcb16772e9"},{"word":"WEB\u30c7\u30b6\u30a4\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Cb50ad663b1947345319ef84cec6e5a91"},{"word":"\u5c02\u9580\u5b66\u6821 \u60c5\u5831","ref":"HS%7Cbookmarkmain%7CORG%7C703fed11094151041380430ce3e55f22"},{"word":"\u518d\u5a5a","ref":"HS%7Cbookmarkmain%7CORG%7C1f8ba6563a214772a43d1a0de921efbe"},{"word":"\u533b\u7642\u4e8b\u52d9","ref":"HS%7Cbookmarkmain%7CORG%7Ca38314aa4e5e5770c3331c90b913414b"}],
    target : true,
    url : "http://ov.pixiv.net/sponsor/?Keywords=",
    apikey : "0049600011",
    
    run : function()
    {
        hybridPlus0049600011.writeKeywords();
    },

    writeKeywords : function(){
        var divCount = 0;
        if (document.getElementById("adingo_keywords_" + this.apikey) != null) {
            divCount++;
            while (document.getElementById("adingo_keywords_" + this.apikey + "_" + (divCount)) != null) {
                divCount++;
            }
        }
        var idPrefix = divCount == 0 ? "" : "_" + divCount;
        document.write("<div id=\"adingo_keywords_" + this.apikey + idPrefix + "\" class=\"adingo_keywords\"></div>");

        var div = document.getElementById("adingo_keywords_" + this.apikey + idPrefix);

        var ul = document.createElement("ul");
        for (var i = 0; i < hybridPlus0049600011.keywordSets.length; i++) {
            var li  = document.createElement("li");
            var a   = document.createElement("a");
            a.setAttribute("href", hybridPlus0049600011.url + encodeURIComponent(unescape(hybridPlus0049600011.keywordSets[i]['word'])) + '&ref=' + hybridPlus0049600011.keywordSets[i]['ref'] + "&e=ut");
            a.setAttribute("rel", "nofollow");
            a.onclick = function() {
                if (adingoDA0049600011!= null && typeof adingoPageTracker != 'undefined') {
                    adingoDA0049600011.adingoClickTracker(this);
                    return false;
                }
            }
            if (hybridPlus0049600011.target) a.setAttribute("target", "_blank");
            a.innerHTML = unescape(hybridPlus0049600011.keywordSets[i]['word']);
            li.appendChild(a);
            ul.appendChild(li);
        }
        div.appendChild(ul);
    },

    addDAScript : function() {
        var script = document.createElement("script");
        script.setAttribute("src", "http://analytics.adingo.jp/pda.php");
        script.setAttribute("type", "text/javascript");
        document.getElementsByTagName("head")[0].appendChild(script); 
    },

    existDAScript : function() {
        var scripts = document.getElementsByTagName("script");
        for (var i = 0; i < scripts.length; i++) {
            if (scripts[i].getAttribute('src') == "http://analytics.adingo.jp/pda.php") return true;
        }
        return false;
    },

    initDA : function(count) {
        if (hybridPlus0049600011.existDAScript() && typeof adingoPageTracker != 'undefined') {
            adingoDA0049600011 = new adingoPageTracker("PDA-496-0008-0049600011", "UTF-8", "00001");
        } else if(count < 10) {
            setTimeout("hybridPlus0049600011.initDA(" + (count + 1) + ")", 100);
        }
    }
}
hybridPlus0049600011.run();
