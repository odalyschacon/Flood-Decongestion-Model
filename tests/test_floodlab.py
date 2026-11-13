import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
import tempfile
import numpy as np
import pandas as pd
from floodlab import terrain_routing,storage_scenario,read_rainfall_csv
from geo import to_utm,to_lonlat

class PhysicsChecks(unittest.TestCase):
    def test_bowl_and_mass_balance(self):
        z=np.array([[5,5,4],[5,0,3],[5,4,2]],dtype=float)
        filled,receiver,order,acc=terrain_routing(z)
        self.assertEqual(filled[1,1],2)
        self.assertEqual(len(set(order)),z.size)
        # Every parent is processed before its child: no cycles, no lost runoff.
        pos={int(c):i for i,c in enumerate(order)}
        for c,p in enumerate(receiver):
            if p>=0:self.assertLess(pos[int(p)],pos[c])
        self.assertAlmostEqual(acc.ravel()[receiver==-1].sum(),z.size)
        result=storage_scenario(receiver,order,100,50,.6,{4:1})
        self.assertAlmostEqual(result['generated_runoff_m3'],27)
        self.assertAlmostEqual(result['stored_m3'],1)
        self.assertAlmostEqual(result['mass_balance_error_m3'],0)

    def test_cascaded_storage_does_not_double_count(self):
        receiver=np.array([-1,0,1]);order=np.array([0,1,2])
        result=storage_scenario(receiver,order,100,10,1,{2:2,1:2})
        self.assertEqual(result['stored_m3'],2)
        self.assertEqual(result['boundary_outflow_m3'],1)
        self.assertEqual(storage_scenario(receiver,order,100,0,.6,{1:100})['stored_m3'],0)
        with self.assertRaises(ValueError):storage_scenario(receiver,order,100,10,1.2)
        with self.assertRaises(ValueError):storage_scenario(receiver,order,100,10,1,{9:5})

    def test_projection_reference_and_roundtrip(self):
        x,y=to_utm(-99,0)
        self.assertAlmostEqual(float(x),500000);self.assertAlmostEqual(float(y),0)
        lon=np.array([-98.57,-98.5,-99.0]);lat=np.array([29.39,29.46,30])
        xx,yy=to_utm(lon,lat);ll,pp=to_lonlat(xx,yy)
        np.testing.assert_allclose(ll,lon,atol=1e-7)
        np.testing.assert_allclose(pp,lat,atol=1e-7)

    def test_rainfall_rejects_overlap_missing_and_mixed_series(self):
        df=pd.DataFrame({'start_utc':['2026-01-01T00:00:00Z','2026-01-01T06:00:00Z'],
                         'end_utc':['2026-01-01T06:00:00Z','2026-01-01T12:00:00Z'],
                         'rain_mm':[3,4],'source':['test']*2,'model':['test']*2,
                         'member':['one']*2,'latitude':[29.5]*2,'longitude':[-98.5]*2})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rain.csv';df.to_csv(path,index=False)
            self.assertEqual(read_rainfall_csv(path).rain_mm.sum(),7)
            for column,value in [('start_utc','2026-01-01T03:00:00Z'),('rain_mm',-1),('member','two')]:
                bad=df.copy();bad.loc[1,column]=value;bad.to_csv(path,index=False)
                with self.assertRaises(ValueError):read_rainfall_csv(path)

if __name__=='__main__': unittest.main()
