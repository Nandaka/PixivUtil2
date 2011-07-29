if (typeof adingoDA0049600011 == 'undefined') {
    var adingoDA0049600011 = null;
}
var hybridPlus0049600011 = {
    keywordSets : [{"word":"\u8cb8\u4f1a\u8b70\u5ba4","ref":"HS%7Cbookmarkmain%7CORG%7Ca449a4949aee387d9dd874d54250e179"},{"word":"\u30cd\u30c3\u30c8\u5bfe\u6226","ref":"HS%7Cbookmarkmain%7CORG%7C7555d054ca195a12a65930b7473354fa"},{"word":"\u96fb\u5b50\u66f8\u7c4d","ref":"HS%7Cbookmarkmain%7CORG%7C849623997ba1f23c441d9c551acb2631"},{"word":"\u540c\u4eba\u8a8c \u8cb7\u53d6","ref":"HS%7Cbookmarkmain%7CORG%7C5e2918da2e1da02315dbc1f5fb250457"},{"word":"\u30d3\u30b8\u30cd\u30b9\u30ed\u30fc\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C255b7699c69cf7f3c87c55d46e8442c4"},{"word":"\u30d5\u30ea\u30fc\u30bd\u30d5\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7C93b6aa6f1e5cbb215c10ef4bd99054f0"},{"word":"\u30b9\u30c8\u30fc\u30ab\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Cb3f3bb71898f052d6ab2019dce4fe036"},{"word":"\u8996\u529b\u77ef\u6b63","ref":"HS%7Cbookmarkmain%7CORG%7Ce3aaf62d91246f99b4a430a7a1eca570"},{"word":"\u540c\u4eba\u8a8c \u5370\u5237","ref":"HS%7Cbookmarkmain%7CORG%7C881dfa9551f70a27e0c00808ff5023fb"},{"word":"\u30cb\u30fc\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7C2deb17b8664a5853d59ee8c4e9e77baf"},{"word":"\u30c7\u30b6\u30a4\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C3513a0b7810412840f1b60fcb16772e9"},{"word":"\u7f8e\u767d\u6d17\u9854","ref":"HS%7Cbookmarkmain%7CORG%7C38c9e05b4bdf067be0995fa2743f7f7c"},{"word":"\u52d5\u753b\u4fdd\u5b58","ref":"HS%7Cbookmarkmain%7CORG%7C9924eb763dbd0671cd798362dd712f03"},{"word":"\u5a5a\u6d3b\u5408\u30b3\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7Cf9a714d1bc23ae789989dcdaf8042c00"},{"word":"\u30cb\u30ad\u30d3\u30b1\u30a2","ref":"HS%7Cbookmarkmain%7CORG%7Cbea4068802de3312a6a47551f3e9b2e3"},{"word":"\u8272\u5f69\u691c\u5b9a","ref":"HS%7Cbookmarkmain%7CORG%7C0e32e315b17715fb080c66bac4523ca5"},{"word":"\u526f\u53ce\u5165","ref":"HS%7Cbookmarkmain%7CORG%7Cb8ad555291cac1cd9590bb4e1e4d2112"},{"word":"\u753b\u50cf\u51e6\u7406","ref":"HS%7Cbookmarkmain%7CORG%7Cd6a5ce0f49de5e3512d81f851e3e1787"},{"word":"\u7b2c\u4e8c\u65b0\u5352","ref":"HS%7Cbookmarkmain%7CORG%7C36de5e50afb8f9ed8c3f6841276472f1"},{"word":"\u591a\u6c57\u75c7","ref":"HS%7Cbookmarkmain%7CORG%7Ce53a601223ef5c510f24f26be74ca3e4"},{"word":"\u901a\u4fe1\u5236\u9ad8\u6821","ref":"HS%7Cbookmarkmain%7CORG%7Cda1fe4a9c28f141cedb592b4c0c376be"},{"word":"\u52d5\u753b\u914d\u4fe1","ref":"HS%7Cbookmarkmain%7CORG%7C3daeccac386beb8ba407633c9a264b0e"},{"word":"\u7121\u6599\u30d6\u30ed\u30b0","ref":"HS%7Cbookmarkmain%7CORG%7C941f13e391224343d7ac59ebe4e5e612"},{"word":"100\u5186PC","ref":"HS%7Cbookmarkmain%7CORG%7C2ba91eca4f7ddec17fb2afd48b8e51fb"},{"word":"\u7121\u6599\u30bb\u30df\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C04cbc78907a7fd07368f0278d1246b2a"}],
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
