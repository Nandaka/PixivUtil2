if (typeof adingoDA0049600011 == 'undefined') {
    var adingoDA0049600011 = null;
}
var hybridPlus0049600011 = {
    keywordSets : [{"word":"\u30aa\u30f3\u30e9\u30a4\u30f3\u30b2\u30fc\u30e0","ref":"HS%7Cbookmarkmain%7CORG%7C5deda74216cba86d1f98d8c2a4bcf1da"},{"word":"\u30a2\u30cb\u30e1\u5236\u4f5c","ref":"HS%7Cbookmarkmain%7CORG%7Cc17703c5df46e775a08ebbe03622b123"},{"word":"\u7121\u6599 \u30d5\u30a1\u30a4\u30eb\u30b5\u30fc\u30d0\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C4867c8f543cd8ea032be84e20981e851"},{"word":"\u5373\u65e5\u30ad\u30e3\u30c3\u30b7\u30f3\u30b0","ref":"HS%7Cbookmarkmain%7CORG%7C1915b48148a1603a786873dc6b4fdca6"},{"word":"\u672c\u6c17\u3067\u75e9\u305b\u305f\u3044","ref":"HS%7Cbookmarkmain%7CORG%7C9278d5b855f2a290c20a924144d6cdfc"},{"word":"\u30af\u30ec\u30b8\u30c3\u30c8\u30ab\u30fc\u30c9","ref":"HS%7Cbookmarkmain%7CORG%7C057a47489b1791c1805e5dabc3500470"},{"word":"\u5f15\u304d\u3053\u3082\u308a","ref":"HS%7Cbookmarkmain%7CORG%7C3afb5bcd5eed3b3642cca71469c49f84"},{"word":"\u5a5a\u6d3b\u5408\u30b3\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7Cf9a714d1bc23ae789989dcdaf8042c00"},{"word":"\u7f8e\u767d\u6d17\u9854","ref":"HS%7Cbookmarkmain%7CORG%7C38c9e05b4bdf067be0995fa2743f7f7c"},{"word":"\u97d3\u56fd\u8a9e","ref":"HS%7Cbookmarkmain%7CORG%7C2f263bd0cea04db47be19883cb396671"},{"word":"\u533b\u7642\u4e8b\u52d9\u8cc7\u683c","ref":"HS%7Cbookmarkmain%7CORG%7Cd980eeddfebec9abd1effde702b39b69"},{"word":"WEB\u30c7\u30b6\u30a4\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Cb50ad663b1947345319ef84cec6e5a91"},{"word":"\u60a9\u307f\u76f8\u8ac7","ref":"HS%7Cbookmarkmain%7CORG%7C5b7728fac0d7e58b670ff343cf8ed7e9"},{"word":"\u751f\u7406\u4e0d\u9806","ref":"HS%7Cbookmarkmain%7CORG%7C425e69afe25d1ac16c3372669d588cc5"},{"word":"\u8102\u80aa\u5438\u5f15","ref":"HS%7Cbookmarkmain%7CORG%7Caa30002999cc23c62b66c64c864b091d"},{"word":"\u8996\u529b\u77ef\u6b63","ref":"HS%7Cbookmarkmain%7CORG%7Ce3aaf62d91246f99b4a430a7a1eca570"},{"word":"\u518d\u5a5a","ref":"HS%7Cbookmarkmain%7CORG%7C1f8ba6563a214772a43d1a0de921efbe"},{"word":"\u8584\u6bdb","ref":"HS%7Cbookmarkmain%7CORG%7C2167aa9c1a9986d9d1c1245c5016f517"},{"word":"\u7121\u6599\u30bb\u30df\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C04cbc78907a7fd07368f0278d1246b2a"},{"word":"\u30a4\u30e9\u30b9\u30c8\u30ec\u30fc\u30bf\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C12a3e920ade4f8173f0f855345362b1e"},{"word":"\u30d5\u30ea\u30fc\u30bd\u30d5\u30c8","ref":"HS%7Cbookmarkmain%7CORG%7C93b6aa6f1e5cbb215c10ef4bd99054f0"},{"word":"\u4e2d\u56fd\u8a9e","ref":"HS%7Cbookmarkmain%7CORG%7C1e645cea1dc60628c83078963431dbca"},{"word":"\u533b\u7642\u4e8b\u52d9","ref":"HS%7Cbookmarkmain%7CORG%7Ca38314aa4e5e5770c3331c90b913414b"},{"word":"\u30a6\u30a7\u30d6\u30c7\u30b6\u30a4\u30f3\u30b9\u30af\u30fc\u30eb","ref":"HS%7Cbookmarkmain%7CORG%7C7c9adef73238a9624ce8eb9e557114a7"},{"word":"\u51fa\u4f1a\u3044","ref":"HS%7Cbookmarkmain%7CORG%7C9ff9e06fc8a3458ca9ba1679afdf2996"}],
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
