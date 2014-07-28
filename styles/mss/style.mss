Map {
  background-color: #b8dee6;
}

#countries {
  ::outline {
    line-color: #85c5d3;
    line-width: 2;
    line-join: round;
  }
  polygon-fill: #fff;
}
#contours {
	[class=3] {
  		[zoom=10] { line-width: 0.2; }
    	[zoom>10][zoom<=11] { line-width: 0.3; }
		[zoom>=13] { line-width: 0.4; }
  }
  [class=2] {
  	[zoom>10][zoom<=12] { line-width: 0.2; }
	[zoom>=13] { line-width: 0.4; }    
  }
  [class=1] {
   [zoom>=13] { line-width: 0.15; } 
  }
}
#relief {
  raster-scaling: bilinear;
  raster-comp-op: multiply;
	raster-opacity: 0.2;
}

#hillshade {
  raster-scaling: bilinear;
  raster-comp-op: multiply;
  raster-opacity:0.5;
}
