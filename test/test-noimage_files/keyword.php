if (typeof adingoDA0049600011 == 'undefined') {
    var adingoDA0049600011 = null;
}
var hybridPlus0049600011 = {
    keywordSets : [{"word":"\u5a5a\u6d3b","ref":"HS%7Cbookmarkmain%7CORG%7C3ab9c020fd2dc91785bfaeaafdfb75ee"},{"word":"\u52d5\u753b\u914d\u4fe1","ref":"HS%7Cbookmarkmain%7CORG%7C3daeccac386beb8ba407633c9a264b0e"},{"word":"\u304a\u898b\u5408\u3044\u30d1\u30fc\u30c6\u30a3\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Ce4c27f8af5449abde50ad34772aad41c"},{"word":"\u591a\u6c57","ref":"HS%7Cbookmarkmain%7CORG%7C12f078582067b3b03ba297d3af016b58"},{"word":"\u7d50\u5a5a\u76f8\u8ac7\u6bd4\u8f03","ref":"HS%7Cbookmarkmain%7CORG%7C841350faca151296761af8438d7b7feb"},{"word":"\u7121\u6599 \u30d5\u30a1\u30a4\u30eb\u30b5\u30fc\u30d0\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C4867c8f543cd8ea032be84e20981e851"},{"word":"\u5927\u5bb9\u91cf\u30c7\u30fc\u30bf \u9001\u4fe1","ref":"HS%7Cbookmarkmain%7CORG%7Cecf24f46312bf2487645587a92efd633"},{"word":"\u82f1\u8a9e\u4e0a\u9054","ref":"HS%7Cbookmarkmain%7CORG%7Cb0ff958ec9cf4e804bcc28c51ba03855"},{"word":"\u30dd\u30b1\u30c3\u30c8WiFi","ref":"HS%7Cbookmarkmain%7CORG%7Cc4978937b23ad25cdcee455b1ff2f960"},{"word":"\u58f0\u512a\u5b66\u6821","ref":"HS%7Cbookmarkmain%7CORG%7Cea984e3c4b9fa03b76d5ce27a1cae30c"},{"word":"\u540c\u4eba\u8a8c \u8cb7\u53d6","ref":"HS%7Cbookmarkmain%7CORG%7C5e2918da2e1da02315dbc1f5fb250457"},{"word":"\u52d5\u753b\u4fdd\u5b58","ref":"HS%7Cbookmarkmain%7CORG%7C9924eb763dbd0671cd798362dd712f03"},{"word":"\u4e2d\u56fd\u8a9e","ref":"HS%7Cbookmarkmain%7CORG%7C1e645cea1dc60628c83078963431dbca"},{"word":"\u770b\u8b77\u58eb \u6c42\u4eba","ref":"HS%7Cbookmarkmain%7CORG%7C9ce92ca666d8b2176c674a7e99c4c3fa"},{"word":"\u80a5\u6e80\u6cbb\u7642","ref":"HS%7Cbookmarkmain%7CORG%7C0d6293633efc4f2a3d6b7fed90ee548f"},{"word":"\u9ad8\u6027\u80fdPC","ref":"HS%7Cbookmarkmain%7CORG%7Cb4071c4c86c46257feca6fad44efeda1"},{"word":"\u7f8e\u767d\u6d17\u9854","ref":"HS%7Cbookmarkmain%7CORG%7C38c9e05b4bdf067be0995fa2743f7f7c"},{"word":"\u30a4\u30f3\u30d7\u30e9\u30f3\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7Cd50de8c9e0ced3dc61400c5f2948e1ac"},{"word":"MMORPG","ref":"HS%7Cbookmarkmain%7CORG%7C6790f16b04993442330a08bfe59dbaca"},{"word":"\u6295\u8cc7\u7528\u7269\u4ef6","ref":"HS%7Cbookmarkmain%7CORG%7Cfe624a0fee1a61d9837943360958febf"},{"word":"\u30a8\u30a2\u30b3\u30f3 \u30af\u30ea\u30fc\u30cb\u30f3\u30b0","ref":"HS%7Cbookmarkmain%7CORG%7C1f1a37fbe606c11247986a2a6ef21aa1"},{"word":"\u751f\u7406\u4e0d\u9806","ref":"HS%7Cbookmarkmain%7CORG%7C425e69afe25d1ac16c3372669d588cc5"},{"word":"\u30db\u30fc\u30e0\u30da\u30fc\u30b8\u4f5c\u6210","ref":"HS%7Cbookmarkmain%7CORG%7C93c5b1ba2159ff6a8f361394bd3b4782"},{"word":"\u3042\u304c\u308a\u75c7","ref":"HS%7Cbookmarkmain%7CORG%7C182d188cc1ea6ecca1c74dca5efed303"},{"word":"\u30c7\u30b8\u30bf\u30eb\u4e00\u773c\u30ec\u30d5","ref":"HS%7Cbookmarkmain%7CORG%7Cf28c5d191700d52abd4433efb8b82c53"}],
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
