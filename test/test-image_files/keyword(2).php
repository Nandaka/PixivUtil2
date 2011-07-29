if (typeof adingoDA0049600017 == 'undefined') {
    var adingoDA0049600017 = null;
}
var hybridPlus0049600017 = {
    keywordSets : [{"word":"\u30a2\u30cb\u30e1\u5236\u4f5c","ref":"HS%7Cillust-in-un%7CORG%7Cc17703c5df46e775a08ebbe03622b123"},{"word":"\u8ca9\u4fc3\u30b0\u30c3\u30ba","ref":"HS%7Cillust-in-un%7CORG%7C30fa35bd9153c1367a7238bd3f348af2"},{"word":"\u30db\u30fc\u30e0\u30da\u30fc\u30b8\u4f5c\u6210","ref":"HS%7Cillust-in-un%7CORG%7C93c5b1ba2159ff6a8f361394bd3b4782"},{"word":"\u8272\u5f69\u691c\u5b9a","ref":"HS%7Cillust-in-un%7CORG%7C0e32e315b17715fb080c66bac4523ca5"}],
    target : true,
    url : "http://ov.pixiv.net/sponsor/?Keywords=",
    apikey : "0049600017",
    
    run : function()
    {
        hybridPlus0049600017.writeKeywords();
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
        for (var i = 0; i < hybridPlus0049600017.keywordSets.length; i++) {
            var li  = document.createElement("li");
            var a   = document.createElement("a");
            a.setAttribute("href", hybridPlus0049600017.url + encodeURIComponent(unescape(hybridPlus0049600017.keywordSets[i]['word'])) + '&ref=' + hybridPlus0049600017.keywordSets[i]['ref'] + "&e=ut");
            a.setAttribute("rel", "nofollow");
            a.onclick = function() {
                if (adingoDA0049600017!= null && typeof adingoPageTracker != 'undefined') {
                    adingoDA0049600017.adingoClickTracker(this);
                    return false;
                }
            }
            if (hybridPlus0049600017.target) a.setAttribute("target", "_blank");
            a.innerHTML = unescape(hybridPlus0049600017.keywordSets[i]['word']);
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
        if (hybridPlus0049600017.existDAScript() && typeof adingoPageTracker != 'undefined') {
            adingoDA0049600017 = new adingoPageTracker("PDA-496-0008-0049600017", "UTF-8", "00001");
        } else if(count < 10) {
            setTimeout("hybridPlus0049600017.initDA(" + (count + 1) + ")", 100);
        }
    }
}
hybridPlus0049600017.run();
