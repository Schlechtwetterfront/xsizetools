// XSIZETools_CppHelpers
// C++ Helpers to speed up .msh exporting.

#include <xsi_application.h>
#include <xsi_context.h>
#include <xsi_pluginregistrar.h>
#include <xsi_status.h>

#include <xsi_string.h>
#include <xsi_argument.h>
#include <xsi_command.h>
#include <xsi_x3dobject.h>
#include <xsi_primitive.h>
#include <xsi_polygonmesh.h>
#include <xsi_geometryaccessor.h>
#include <xsi_longarray.h>
#include <xsi_floatarray.h>
#include <xsi_doublearray.h>
#include <xsi_clusterproperty.h>
#include <xsi_envelopeweight.h>

#include <xsi_utils.h>


// Change callback for different SDK versions (x86 version needs to support older versions of XSI and only newer versions have x64 support).
#ifdef _WIN64
#define CALLBACK SICALLBACK
#else
#define CALLBACK XSIPLUGINCALLBACK CStatus
#endif

using namespace XSI; 

CValueArray NodesPerPoint(CGeometryAccessor ga);

CALLBACK XSILoadPlugin( PluginRegistrar& in_reg )
{
	in_reg.PutAuthor(L"Benedikt 'Schlechtwetterfront' Schatz");
	in_reg.PutName(L"CGeoAccessorWrappers");
	in_reg.PutVersion(0,8);
	
	in_reg.RegisterCommand(L"CGA_GetVertexIndices",L"CGA_GetVertexIndices");
	in_reg.RegisterCommand(L"CGA_GetNodeIndices",L"CGA_GetNodeIndices");
	in_reg.RegisterCommand(L"CGA_GetVertexPositions",L"CGA_GetVertexPositions");
	in_reg.RegisterCommand(L"CGA_GetPolygonVerticesCount",L"CGA_GetPolygonVerticesCount");
	in_reg.RegisterCommand(L"CGA_GetNodeNormals",L"CGA_GetNodeNormals");
	in_reg.RegisterCommand(L"CGA_GetUV0",L"CGA_GetUV0");
	in_reg.RegisterCommand(L"CGA_GetVertexColors0",L"CGA_GetVertexColors0");
	in_reg.RegisterCommand(L"CGA_GetNodeVertexPositions",L"CGA_GetNodeVertexPositions");
	in_reg.RegisterCommand(L"CGA_GetWeights0",L"CGA_GetWeights0");
	in_reg.RegisterCommand(L"CGA_GetWeightsZE",L"CGA_GetWeightsZE");
	in_reg.RegisterCommand(L"CGA_GetDeformers0",L"CGA_GetDeformers0");
	in_reg.RegisterCommand(L"CGA_GetNodesPerPoint",L"CGA_GetNodesPerPoint");

	return CStatus::OK;
}

CALLBACK XSIUnloadPlugin( const PluginRegistrar& in_reg )
{
	CString strPluginName;
	strPluginName = in_reg.GetName();
	Application().LogMessage(strPluginName + L" has been unloaded.",siVerboseMsg);
	return CStatus::OK;
}

CALLBACK CGA_GetNodeVertexPositions_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oArgs.Add(L"worldCoords");
	oCmd.PutDescription(L"Returns the corresponding vertex position for every node in an array. If worldCoords is True, multiply with scale.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodeVertexPositions_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	bool worldCoords = args[1];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	// get poly node indices
	CLongArray nodeindices;
	ga.GetNodeIndices(nodeindices);
	// get poly vert indices
	CLongArray vertindices;
	ga.GetVertexIndices(vertindices);
	// get vert positions
	CDoubleArray vertpos;
	ga.GetVertexPositions(vertpos);
	//
	CFloatArray positions;
	positions.Resize(nodeindices.GetCount()*3);
	// format
	if(worldCoords == true) {
		MATH::CTransformation transform = ga.GetTransform();
		double sX = transform.GetSclX();
		double sY = transform.GetSclY();
		double sZ = transform.GetSclZ();
		for(long i=0; i<vertindices.GetCount(); i++) {
			// Order Vertices after Nodes.
			long nodeindex = nodeindices[i];
			long vertindex = vertindices[i];
			positions[nodeindex*3] = vertpos[vertindex*3]*sX;
			positions[nodeindex*3+1] = vertpos[vertindex*3+1]*sY;
			positions[nodeindex*3+2] = vertpos[vertindex*3+2]*sZ;
		}
	}
	else {
		for(long i=0; i<vertindices.GetCount(); i++) {
			long nodeindex = nodeindices[i];
			long vertindex = vertindices[i];
			positions[nodeindex*3] = vertpos[vertindex*3];
			positions[nodeindex*3+1] = vertpos[vertindex*3+1];
			positions[nodeindex*3+2] = vertpos[vertindex*3+2];
		}
	}
	ctxt.PutAttribute( L"ReturnValue", positions);
	return CStatus::OK;
}

CALLBACK CGA_GetVertexIndices_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetVertexIndices. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetVertexIndices_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CLongArray vertindices;
	ga.GetVertexIndices(vertindices);
	ctxt.PutAttribute( L"ReturnValue", vertindices);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetNodeIndices_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetNodeIndices. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodeIndices_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CLongArray nodeindices;
	ga.GetNodeIndices(nodeindices);
	ctxt.PutAttribute( L"ReturnValue", nodeindices);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetVertexPositions_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetVertexPositions. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetVertexPositions_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CDoubleArray vertpositions;
	ga.GetVertexPositions(vertpositions);
	long doublecount = vertpositions.GetCount();
	CFloatArray vertpos;
	vertpos.Resize(doublecount);
	for(long i=0; i<doublecount; i++) {
		vertpos[i] = vertpositions[i];
	}
	ctxt.PutAttribute( L"ReturnValue", vertpos);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetPolygonVerticesCount_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetVerticesCount. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetPolygonVerticesCount_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CLongArray polyvertcnt;
	ga.GetPolygonVerticesCount(polyvertcnt);
	ctxt.PutAttribute( L"ReturnValue", polyvertcnt);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetNodeNormals_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"\"Wrapper\" for CGeometryAccessor method GetNodeNormals. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodeNormals_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh obj = args[0];
	CGeometryAccessor ga = obj.GetGeometryAccessor();
	CFloatArray normals;
	ga.GetNodeNormals(normals);
	ctxt.PutAttribute( L"ReturnValue", normals);
	// Return CStatus::Fail if you want to raise a script error
	return CStatus::OK;
}

CALLBACK CGA_GetUV0_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"Returns UV values as CFloatArray of the first UV cluster. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetUV0_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray uvs = ga.GetUVs();
	ClusterProperty uv = uvs[0];
	CFloatArray uvvalues;
	uv.GetValues(uvvalues);
	ctxt.PutAttribute( L"ReturnValue", uvvalues );
	return CStatus::OK;
}

CALLBACK CGA_GetVertexColors0_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"Returns vertex color values of the first vertex color cluster. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetVertexColors0_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray uvs = ga.GetVertexColors();
	ClusterProperty uv = uvs[0];
	CFloatArray vcvalues;
	uv.GetValues(vcvalues);
	ctxt.PutAttribute( L"ReturnValue", vcvalues );
	return CStatus::OK;
}
CALLBACK CGA_GetWeights0_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"Returns Weight values as CFloatArray of the first UV cluster. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetWeights0_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray envWeights = ga.GetEnvelopeWeights();
	EnvelopeWeight envWeight = envWeights[0];
	CFloatArray weights;
	envWeight.GetValues(weights);
	ctxt.PutAttribute( L"ReturnValue", weights);
	return CStatus::OK;
}

CALLBACK CGA_GetWeightsZE_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"Returns ( (elemcount), (weights), (deformerindices), (deformernames) ). A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetWeightsZE_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CRefArray envWeights = ga.GetEnvelopeWeights();
	EnvelopeWeight envWeight = envWeights[0];
	CFloatArray weights;
	envWeight.GetValues(weights);
	long valsize = envWeight.GetValueSize();
	xsi.LogMessage( CString(valsize));
	long geosize = weights.GetCount() / valsize;
	// Declare arrays.
	CValueArray def_names(valsize);

	CRefArray deformers = envWeight.GetDeformers();
	def_names.Resize(deformers.GetCount());
	for(long j=0; j<deformers.GetCount(); j++) {
		SIObject siobj(deformers[j]);
		def_names[j] = siobj.GetName();
	}
	CValueArray weights_defs(3);
	weights_defs[0] = valsize;
	weights_defs[1] = weights;
	weights_defs[2] = def_names;
	ctxt.PutAttribute( L"ReturnValue", weights_defs);
	return CStatus::OK;
}

CALLBACK CGA_GetNodesPerPoint_Init( CRef& in_ctxt )
{
	Context ctxt( in_ctxt );
	Command oCmd;
	oCmd = ctxt.GetSource();
	ArgumentArray oArgs;
	oArgs = oCmd.GetArguments();
	oArgs.Add(L"polymsh");
	oCmd.PutDescription(L"Returns Nodes per Point. A PolygonMesh needs to be passed as argument.");
	oCmd.EnableReturnValue(true);

	return CStatus::OK;
}

CALLBACK CGA_GetNodesPerPoint_Execute( CRef& in_ctxt )
{
	//Stuff.
	Context ctxt( in_ctxt );
	Application xsi;
	// arguments
	CValueArray args = ctxt.GetAttribute(L"Arguments");
	PolygonMesh geo = args[0];
	CGeometryAccessor ga = geo.GetGeometryAccessor();
	CValueArray ordered;
	// get poly node indices
	CLongArray nodeindices;
	ga.GetNodeIndices(nodeindices);
	// get poly vert indices
	CLongArray vertindices;
	ga.GetVertexIndices(vertindices);
	xsi.LogMessage( CString(nodeindices.GetCount()));
	xsi.LogMessage( CString(vertindices.GetCount()));
	ordered.Resize( nodeindices.GetCount() );
	for(long j=0; j<nodeindices.GetCount(); j++) {
		long vertindex = vertindices[j];
		long nodeindex = nodeindices[j];
		ordered[nodeindex] = vertindex;
	}
	ctxt.PutAttribute( L"ReturnValue", ordered);
	return CStatus::OK;
}