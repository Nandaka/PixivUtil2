if (typeof adingoDA0049600011 == 'undefined') {
    var adingoDA0049600011 = null;
}
var hybridPlus0049600011 = {
    keywordSets : [{"word":"\u30c7\u30b6\u30a4\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C3513a0b7810412840f1b60fcb16772e9"},{"word":"\u8102\u80aa\u5438\u5f15","ref":"HS%7Cbookmarkmain%7CORG%7Caa30002999cc23c62b66c64c864b091d"},{"word":"\u304c\u3093\u4fdd\u967a","ref":"HS%7Cbookmarkmain%7CORG%7Ca48ec19024b3bde65078bbbda01afd6c"},{"word":"\u30dd\u30b1\u30c3\u30c8WiFi","ref":"HS%7Cbookmarkmain%7CORG%7Cc4978937b23ad25cdcee455b1ff2f960"},{"word":"\u5373\u65e5\u878d\u8cc7","ref":"HS%7Cbookmarkmain%7CORG%7C9bb23130e0366b5c21dfbba48106f16b"},{"word":"\u672c\u6c17\u3067\u75e9\u305b\u305f\u3044","ref":"HS%7Cbookmarkmain%7CORG%7C9278d5b855f2a290c20a924144d6cdfc"},{"word":"\u60a9\u307f\u76f8\u8ac7","ref":"HS%7Cbookmarkmain%7CORG%7C5b7728fac0d7e58b670ff343cf8ed7e9"},{"word":"\u30c7\u30b6\u30a4\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Caa6851ddfa494e996cd98066e3e7c758"},{"word":"\u96fb\u5b50\u66f8\u7c4d","ref":"HS%7Cbookmarkmain%7CORG%7C849623997ba1f23c441d9c551acb2631"},{"word":"\u4e0d\u767b\u6821","ref":"HS%7Cbookmarkmain%7CORG%7Cdcaeff4a8d9d61240386a3636742d9d1"},{"word":"\u8cc3\u8cb8\u7269\u4ef6\u63a2\u3057","ref":"HS%7Cbookmarkmain%7CORG%7Ce9c44ace6255360e5bd0a7f0e4242dce"},{"word":"\u8996\u529b\u77ef\u6b63","ref":"HS%7Cbookmarkmain%7CORG%7Ce3aaf62d91246f99b4a430a7a1eca570"},{"word":"\u6c57 \u81ed\u3044","ref":"HS%7Cbookmarkmain%7CORG%7Cae5819f52a4568b24cf357a15ea079ea"},{"word":"\u9ad8\u7d1a\u30de\u30f3\u30b7\u30e7\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C6109436f01b176e649a92e0f81d1c150"},{"word":"\u5c02\u9580\u5b66\u6821 \u60c5\u5831","ref":"HS%7Cbookmarkmain%7CORG%7C703fed11094151041380430ce3e55f22"},{"word":"WEB\u30c7\u30b6\u30a4\u30ca\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7Cb50ad663b1947345319ef84cec6e5a91"},{"word":"\u6fc0\u5b89 PC","ref":"HS%7Cbookmarkmain%7CORG%7Ca044be5a24d9e36bf293fbe3f1a32b70"},{"word":"\u88fd\u672c","ref":"HS%7Cbookmarkmain%7CORG%7C29edb091574e853baa5db99780731822"},{"word":"\u9ad8\u6027\u80fdPC","ref":"HS%7Cbookmarkmain%7CORG%7Cb4071c4c86c46257feca6fad44efeda1"},{"word":"\u753b\u50cf\u51e6\u7406","ref":"HS%7Cbookmarkmain%7CORG%7Cd6a5ce0f49de5e3512d81f851e3e1787"},{"word":"\u591a\u6c57\u75c7","ref":"HS%7Cbookmarkmain%7CORG%7Ce53a601223ef5c510f24f26be74ca3e4"},{"word":"\u97d3\u56fd\u8a9e","ref":"HS%7Cbookmarkmain%7CORG%7C2f263bd0cea04db47be19883cb396671"},{"word":"\u30de\u30f3\u30b9\u30ea\u30fc\u30de\u30f3\u30b7\u30e7\u30f3","ref":"HS%7Cbookmarkmain%7CORG%7C0af31e67bbff0c1fa09dc98adc96017e"},{"word":"\u7121\u6599\u30a2\u30d0\u30bf\u30fc","ref":"HS%7Cbookmarkmain%7CORG%7C4623f3d3a3146d064d572f10264e9ae7"},{"word":"\u5a5a\u6d3b","ref":"HS%7Cbookmarkmain%7CORG%7C3ab9c020fd2dc91785bfaeaafdfb75ee"}],
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
