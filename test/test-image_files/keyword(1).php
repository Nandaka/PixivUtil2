if (typeof adingoDA0049600016 == 'undefined') {
    var adingoDA0049600016 = null;
}
var hybridPlus0049600016 = {
    keywordSets : [{"word":"\u540c\u4eba\u8a8c\u4f5c\u308b","ref":"HS%7Cillust-in-up%7CORG%7C62181a80f9602a9fd7b04e6ef426dd90"},{"word":"\u30db\u30fc\u30e0\u30da\u30fc\u30b8\u4f5c\u6210","ref":"HS%7Cillust-in-up%7CORG%7C93c5b1ba2159ff6a8f361394bd3b4782"},{"word":"\u540c\u4eba\u8a8c \u5370\u5237","ref":"HS%7Cillust-in-up%7CORG%7C881dfa9551f70a27e0c00808ff5023fb"},{"word":"\u30c7\u30b6\u30a4\u30ca\u30fc","ref":"HS%7Cillust-in-up%7CORG%7Caa6851ddfa494e996cd98066e3e7c758"}],
    target : true,
    url : "http://ov.pixiv.net/sponsor/?Keywords=",
    apikey : "0049600016",
    
    run : function()
    {
        hybridPlus0049600016.writeKeywords();
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
        for (var i = 0; i < hybridPlus0049600016.keywordSets.length; i++) {
            var li  = document.createElement("li");
            var a   = document.createElement("a");
            a.setAttribute("href", hybridPlus0049600016.url + encodeURIComponent(unescape(hybridPlus0049600016.keywordSets[i]['word'])) + '&ref=' + hybridPlus0049600016.keywordSets[i]['ref'] + "&e=ut");
            a.setAttribute("rel", "nofollow");
            a.onclick = function() {
                if (adingoDA0049600016!= null && typeof adingoPageTracker != 'undefined') {
                    adingoDA0049600016.adingoClickTracker(this);
                    return false;
                }
            }
            if (hybridPlus0049600016.target) a.setAttribute("target", "_blank");
            a.innerHTML = unescape(hybridPlus0049600016.keywordSets[i]['word']);
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
        if (hybridPlus0049600016.existDAScript() && typeof adingoPageTracker != 'undefined') {
            adingoDA0049600016 = new adingoPageTracker("PDA-496-0008-0049600016", "UTF-8", "00001");
        } else if(count < 10) {
            setTimeout("hybridPlus0049600016.initDA(" + (count + 1) + ")", 100);
        }
    }
}
hybridPlus0049600016.run();
