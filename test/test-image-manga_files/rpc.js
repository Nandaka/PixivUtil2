//======================================
//	リクエスト
//======================================
function sendRequest(url, me, pars, comp){
	var myAjax = new Ajax.Request(
		url, 
		{
			method: me, 
			parameters: pars, 
			onComplete: comp
		});
}
