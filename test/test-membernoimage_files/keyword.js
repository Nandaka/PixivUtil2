if (typeof adingoDA0049600011 == 'undefined') {
    var adingoDA0049600011 = null;
}
var hybridPlus0049600011 = {
    keywordSets : [{"word":"\u30c7\u30b6\u30a4\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C3513a0b7810412840f1b60fcb16772e9"},{"word":"\u88fd\u672c","ref":"HS%7Cbookmarkmain%7CORG%7C29edb091574e853baa5db99780731822"},{"word":"\u518d\u5a5a","ref":"HS%7Cbookmarkmain%7CORG%7C1f8ba6563a214772a43d1a0de921efbe"},{"word":"\u51fa\u4f1a\u3044","ref":"HS%7Cbookmarkmain%7CORG%7C9ff9e06fc8a3458ca9ba1679afdf2996"},{"word":"\u6295\u8cc7\u7528\u7269\u4ef6","ref":"HS%7Cbookmarkmain%7CORG%7Cfe624a0fee1a61d9837943360958febf"},{"word":"\u30ef\u30ad\u30ac","ref":"HS%7Cbookmarkmain%7CORG%7Cce473389886a5fa585cbc7ce81b33960"},{"word":"\u591a\u6c57\u75c7","ref":"HS%7Cbookmarkmain%7CORG%7Ce53a601223ef5c510f24f26be74ca3e4"},{"word":"\u30cb\u30fc\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7C2deb17b8664a5853d59ee8c4e9e77baf"},{"word":"\u30ef\u30ad\u8131\u6bdb","ref":"HS%7Cbookmarkmain%7CORG%7C0c8bdea61d5a4b0c604f8fd81be33c83"},{"word":"\u82f1\u8a9e\u4e0a\u9054","ref":"HS%7Cbookmarkmain%7CORG%7Cb0ff958ec9cf4e804bcc28c51ba03855"},{"word":"\u533b\u7642\u4e8b\u52d9\u8cc7\u683c","ref":"HS%7Cbookmarkmain%7CORG%7Cd980eeddfebec9abd1effde702b39b69"},{"word":"\u30ad\u30e3\u30c3\u30b7\u30f3\u30b0","ref":"HS%7Cbookmarkmain%7CORG%7C83d18cf0b6c5229801ee7e2691cfa275"},{"word":"\u8996\u529b\u77ef\u6b63","ref":"HS%7Cbookmarkmain%7CORG%7Ce3aaf62d91246f99b4a430a7a1eca570"},{"word":"\u30a4\u30f3\u30d7\u30e9\u30f3\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7Cd50de8c9e0ced3dc61400c5f2948e1ac"},{"word":"DVD\u30ec\u30f3\u30bf\u30eb","ref":"HS%7Cbookmarkmain%7CORG%7C8ce17a796aab0e7a25ec8571985e7875"},{"word":"\u540c\u4eba\u8a8c \u8cb7\u53d6","ref":"HS%7Cbookmarkmain%7CORG%7C5e2918da2e1da02315dbc1f5fb250457"},{"word":"\u30af\u30ec\u30b8\u30c3\u30c8\u30ab\u30fc\u30c9","ref":"HS%7Cbookmarkmain%7CORG%7C057a47489b1791c1805e5dabc3500470"},{"word":"\u304a\u898b\u5408\u3044\u30d1\u30fc\u30c6\u30a3\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Ce4c27f8af5449abde50ad34772aad41c"},{"word":"\u6c57 \u81ed\u3044","ref":"HS%7Cbookmarkmain%7CORG%7Cae5819f52a4568b24cf357a15ea079ea"},{"word":"\u5c02\u9580\u5b66\u6821 \u60c5\u5831","ref":"HS%7Cbookmarkmain%7CORG%7C703fed11094151041380430ce3e55f22"},{"word":"\u533b\u7642\u4e8b\u52d9","ref":"HS%7Cbookmarkmain%7CORG%7Ca38314aa4e5e5770c3331c90b913414b"},{"word":"\u30da\u30f3\u30bf\u30d6\u30ec\u30c3\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7Ca7c562279555211c838d6dfd1edeadaa"},{"word":"\u753b\u50cf\u51e6\u7406","ref":"HS%7Cbookmarkmain%7CORG%7Cd6a5ce0f49de5e3512d81f851e3e1787"},{"word":"\u30cd\u30c3\u30c8\u5bfe\u6226","ref":"HS%7Cbookmarkmain%7CORG%7C7555d054ca195a12a65930b7473354fa"},{"word":"\u591a\u6c57","ref":"HS%7Cbookmarkmain%7CORG%7C12f078582067b3b03ba297d3af016b58"}],
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
