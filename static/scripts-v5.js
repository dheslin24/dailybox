//function myMove() {
//  var elem = document.getElementById("myAnimation");
//  var pos = 0;
//  var id = setInterval(frame, 10);
//  function frame() {
//    if (pos == 350) {
//      clearInterval(id);
//    } else {
//      pos++;
//      elem.style.top = pos + 'px';
//      elem.style.left = pos + 'px';
//    }
//  }
//}

function empty()
{
    var empt = document.getElementById("rand").value;
    console.log(empt);
    console.log("got to empt");
    if (empt == "")
    {
       alert("Please enter # of boxes");
       return false;
    }
       return true;
}


(function ($) {
    //
    // Zachary Johnson
    // https://www.zachstronaut.com/posts/2009/12/21/happy-xmas-winternet.html
    // December 2009
    //
    
    // DHDHDH
    // add back all references to text shadow support to get snowflakes back to white
    var ww = 0;
    var wh = 0;
    var maxw = 0;
    var minw = 0;
    var maxh = 0;
    //var textShadowSupport = true;
    var xv = 0;
    //var image = document.createElement('img');
    //var image = document.getElementById("x");
    var image = new Image()
    //var imagestring = "<img src=\"" + image.getAttribute("src") + "\">";
    //var imagestring2 = "<img src='https://www.kindpng.com/picc/m/31-311472_turkey-leg-clipart-transparent-hd-png-download.png'/>";
    image.src = 'https://www.kindpng.com/picc/m/31-311472_turkey-leg-clipart-transparent-hd-png-download.png';
    //image.height = 200
    //image.width = 200
    // var src = document.getElementById("x");
    // document.appendChild(img);
    // var drum = document.getElementById(image).appendChild(image)
 
    //  -`-`-`-`-`-`-`-`-``-`-`-`-`-`-`-`-`-`            //
    //  Use this great site to convert to surrogate pair //
    //  For emojis to work
    //  http://www.russellcottrell.com/greek/utilities/surrogatepaircalculator.htm
    //  -`-`-`-`-`-`-`-`-`-`-`--`-`-`-`-`-`-``-`         //

    // var snowflakes = ["\u2744", "\u2745", "\u2746"];
    // var snowflakes = ["$", "\u2744", "\u2745", "\u2746"];
    // var myanimation = document.getElementById("myImg");
    // var snowflakes = ["$",  $(image).attr('src')];
    // var snowflakes = ["\uD83C\uDF57"]; // <-- turkey legs
    // var snowflakes = ["\uD83C\uDF84", "\u2744", "\u2603", "\uD83C\uDF85"]; // <-- xmas tree
    var snowflakes = ["\uD83C\uDFC8", "\uD83C\uDF76", "\uD83C\uDF7B", "\uD83C\uDF77", "\uD83E\uDD43", "\uD83E\uDD64"]
    var prevTime;
    var absMax = 5;
    var flakeCount = 0;
    
    $(init);

    function init()
    {
        var detectSize = function ()
        {
            ww = $(window).width();
            wh = $(window).height();
            
            maxw = ww + 300;
            minw = -300;
            maxh = wh + 300;
        };
        
        detectSize();
        
        $(window).resize(detectSize);
        
        if (!$('body').css('textShadow'))
        {
            textShadowSupport = false;
        }
        
        var i = 5;
        while (i--)
        {
            addFlake(true);
        }
        
        prevTime = new Date().getTime();
        setInterval(move, 50);
    }

    function addFlake(initial)
    {
        flakeCount++;
        
        var sizes = [
            {
                r: 1.0,
                css: {
                    fontSize: 15 + Math.floor(Math.random() * 20) + 'px',
                    //textShadow: '9999px 0 0 rgba(238, 238, 238, 0.5)'
                },
                v: 2
            },
            {
                r: 0.6,
                css: {
                    fontSize: 20 + Math.floor(Math.random() * 20) + 'px',
                    //textShadow: '9999px 0 2px #eee'
                },
                v: 6
            },
            {
                r: 0.2,
                css: {
                    fontSize: 30 + Math.floor(Math.random() * 30) + 'px',
                    //textShadow: '9999px 0 6px #eee'
                },
                v: 12
            },
            {
                r: 0.1,
                css: {
                    fontSize: 50 + Math.floor(Math.random() * 50) + 'px',
                    //textShadow: '9999px 0 24px #eee'
                },
                v: 20
            }
        ];
    
        var $nowflake = $('<span class="winternetz">' + snowflakes[Math.floor(Math.random() * snowflakes.length)] + '</span>').css(
            {
                /*fontFamily: 'Wingdings',
                color: '#eee',
                display: 'block',*/
                position: 'fixed',
                background: 'transparent',
                width: 'auto',
                height: 'auto',
                margin: '0',
                padding: '0'
                //textAlign: 'left',
                //zIndex: 9999
            }
        );
        
        /*
        if (textShadowSupport)
        {
            $nowflake.css('textIndent', '-9999px');
        }
        */
        
        var r = Math.random();
    
        var i = sizes.length;
        
        var v = 0;
        
        while (i--)
        {
            if (r < sizes[i].r)
            {
                v = sizes[i].v;
                $nowflake.css(sizes[i].css);
                break;
            }
        }
    
        var x = (-300 + Math.floor(Math.random() * (ww + 300)));
        
        var y = 0;
        if (typeof initial == 'undefined' || !initial)
        {
            y = -300;
        }
        else
        {
            y = (-300 + Math.floor(Math.random() * (wh + 300)));
        }
    
        $nowflake.css(
            {
                left: x + 'px',
                top: y + 'px'
            }
        );
        
        $nowflake.data('x', x);
        $nowflake.data('y', y);
        $nowflake.data('v', v);
        $nowflake.data('half_v', Math.round(v * 0.5));
        
        $('body').append($nowflake);  // DH messed with here
    }

    
    function move()
    {
        if (Math.random() > 0.8)
        {
            xv += -1 + Math.random() * 2;
            
            if (Math.abs(xv) > 3)
            {
                xv = 3 * (xv / Math.abs(xv));
            }
        }
        
        // Throttle code
        var newTime = new Date().getTime();
        var diffTime = newTime - prevTime;
        prevTime = newTime;
        
        if (diffTime < 155 && flakeCount < absMax)
        {
            addFlake();
        }
        else if (diffTime > 250)
        {
            $('span.winternetz:first').remove();
            //$('span.winternetz2:first').remove();
            flakeCount--;
        }
        
        $('span.winternetz').each(
            function ()
            {
                var x = $(this).data('x');
                var y = $(this).data('y');
                var v = $(this).data('v');
                var half_v = $(this).data('half_v');
                
                y += v;
                
                x += Math.round(xv * v);
                x += -half_v + Math.round(Math.random() * v);
                
                // because flakes are rotating, the origin could be +/- the size of the flake offset
                if (x > maxw)
                {
                    x = -300;
                }
                else if (x < minw)
                {
                    x = ww;
                }
                
                if (y > maxh)
                {
                    $(this).remove();
                    flakeCount--;
                    
                    addFlake();
                }
                else
                {
                    $(this).data('x', x);
                    $(this).data('y', y);

                    $(this).css(
                        {
                            left: x + 'px',
                            top: y + 'px'
                        }
                    );
                    
                    // only spin biggest three flake sizes
                    if (v >= 6)
                    {
                        $(this).animate({rotate: '+=' + half_v + 'deg'}, 0);
                    }
                }
            }
        );
    }
})(jQuery);

